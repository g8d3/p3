/**
 * Docker-based sandbox implementation.
 * 
 * Lightweight: uses a minimal Node image, resource-limited containers.
 * Upgraded from s50 sandbox with better resource management.
 */

import { execSync, spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, writeFileSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { SandboxProvider, SandboxInstance, SandboxConfig, SandboxMetrics, CommandResult } from './interface.js';

const DOCKER_IMAGE = 'p3-agent-sandbox:latest';

export class DockerSandboxProvider implements SandboxProvider {
  readonly name = 'docker';
  
  private imageBuilt = false;

  async isAvailable(): Promise<boolean> {
    try {
      execSync('docker info --format "{{.ServerVersion}}"', { stdio: 'pipe', timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }

  async getInfo() {
    const version = execSync('docker version --format "{{.Server.Version}}"', { encoding: 'utf-8' }).trim();
    return { version, features: ['namespace-isolation', 'cgroup-limits', 'readonly-root'] };
  }

  async ensureImage(): Promise<void> {
    if (this.imageBuilt) return;
    try {
      execSync(`docker image inspect ${DOCKER_IMAGE}`, { stdio: 'pipe' });
    } catch {
      console.log('[sandbox] Building minimal sandbox image...');
      const dockerfile = `
FROM alpine:3.19
RUN apk add --no-cache nodejs npm git curl bash jq ca-certificates && \
    adduser -D -h /home/agent agent
USER agent
WORKDIR /workspace
`;
      const tmpDir = mkdtempSync(join(tmpdir(), 'sandbox-build-'));
      writeFileSync(join(tmpDir, 'Dockerfile'), dockerfile);
      execSync(`docker build -t ${DOCKER_IMAGE} ${tmpDir}`, { stdio: 'inherit', timeout: 120000 });
    }
    this.imageBuilt = true;
  }

  async create(config: SandboxConfig = {}): Promise<SandboxInstance> {
    await this.ensureImage();
    const id = `agent-${randomUUID().slice(0, 8)}`;
    return new DockerSandboxInstance(id, this, config);
  }
}

class DockerSandboxInstance implements SandboxInstance {
  readonly id: string;
  readonly provider: DockerSandboxProvider;
  private containerId: string | null = null;
  private config: SandboxConfig;
  private createdAt: number;
  private active = false;

  constructor(id: string, provider: DockerSandboxProvider, config: SandboxConfig) {
    this.id = id;
    this.provider = provider;
    this.config = config;
    this.createdAt = Date.now();
  }

  private async ensureRunning(): Promise<string> {
    if (this.containerId) return this.containerId;

    const args = ['run', '-d', '--rm'];
    
    // Resource limits
    const memMb = this.config.memoryLimitMb ?? 512;
    const cpuLimit = this.config.cpuLimit ?? 1;
    args.push('--memory', `${memMb}m`, '--cpus', String(cpuLimit));
    
    // Network
    if (this.config.networkEnabled) {
      args.push('--network', 'host');
    } else {
      args.push('--network', 'none');
    }
    
    // Security
    args.push('--security-opt', 'no-new-privileges:true',
      '--cap-drop', 'ALL',
      '--read-only',
      '--tmpfs', '/tmp:size=128m');
    
    // Env vars
    if (this.config.env) {
      for (const [k, v] of Object.entries(this.config.env)) {
        args.push('-e', `${k}=${v}`);
      }
    }
    
    // Image and command
    args.push(DOCKER_IMAGE, 'sleep', String(this.config.timeoutSeconds ?? 3600));
    
    const output = execSync(`docker ${args.join(' ')}`, { encoding: 'utf-8' }).trim();
    this.containerId = output;
    this.active = true;
    return this.containerId;
  }

  async exec(command: string, args?: string[]): Promise<CommandResult> {
    const cid = await this.ensureRunning();
    const start = Date.now();
    
    try {
      const cmd = args ? `${command} ${args.map(a => `"${a}"`).join(' ')}` : command;
      const output = execSync(`docker exec ${cid} /bin/sh -c ${JSON.stringify(cmd)}`, {
        encoding: 'utf-8',
        timeout: (this.config.timeoutSeconds ?? 60) * 1000,
        maxBuffer: 10 * 1024 * 1024,
      });
      
      return {
        exitCode: 0,
        stdout: output,
        stderr: '',
        durationMs: Date.now() - start,
      };
    } catch (err: any) {
      return {
        exitCode: err.status ?? 1,
        stdout: err.stdout?.toString() ?? '',
        stderr: err.stderr?.toString() ?? err.message,
        durationMs: Date.now() - start,
      };
    }
  }

  async execStream(
    command: string,
    args?: string[],
    onData?: (chunk: string) => void
  ): Promise<CommandResult> {
    const cid = await this.ensureRunning();
    const start = Date.now();
    
    return new Promise((resolve) => {
      const cmd = args ? `${command} ${args.map(a => `"${a}"`).join(' ')}` : command;
      const child = spawn('docker', ['exec', '-i', cid, '/bin/sh', '-c', cmd], {
        stdio: ['pipe', 'pipe', 'pipe'],
      });
      
      let stdout = '';
      let stderr = '';
      
      child.stdout?.on('data', (chunk: Buffer) => {
        const text = chunk.toString();
        stdout += text;
        onData?.(text);
      });
      
      child.stderr?.on('data', (chunk: Buffer) => {
        stderr += chunk.toString();
      });
      
      child.on('close', (exitCode) => {
        resolve({
          exitCode: exitCode ?? 1,
          stdout,
          stderr,
          durationMs: Date.now() - start,
        });
      });
      
      child.on('error', (err) => {
        resolve({
          exitCode: 1,
          stdout,
          stderr: err.message,
          durationMs: Date.now() - start,
        });
      });
    });
  }

  async writeFile(path: string, content: string | Buffer): Promise<void> {
    const cid = await this.ensureRunning();
    const safePath = path.startsWith('/tmp') ? path : `/tmp/${path.replace(/^\/+/, '').replace(/\//g, '_')}`;
    const contentStr = Buffer.isBuffer(content) ? content.toString() : content;
    execSync(`docker exec -i ${cid} sh -c "cat > '${safePath}'"`, {
      input: contentStr,
      timeout: 10000,
    });
  }

  async readFile(path: string): Promise<Buffer> {
    const cid = await this.ensureRunning();
    const safePath = path.startsWith('/tmp') ? path : `/tmp/${path.replace(/^\/+/, '').replace(/\//g, '_')}`;
    const b64 = execSync(`docker exec ${cid} sh -c "cat '${safePath}' | base64"`, {
      timeout: 10000,
    }).toString().trim();
    return Buffer.from(b64, 'base64');
  }

  async getMetrics(): Promise<SandboxMetrics> {
    if (!this.containerId || !this.active) {
      return { cpuPercent: 0, memoryMb: 0, pid: 0, uptimeSeconds: 0 };
    }
    
    try {
      const stats = execSync(
        `docker stats --no-stream --format "{{.CPUPerc}}|{{.MemUsage}}" ${this.containerId}`,
        { encoding: 'utf-8', timeout: 5000 }
      ).trim();
      
      const [cpuStr, memStr] = stats.split('|');
      const cpuPercent = parseFloat(cpuStr?.replace('%', '') ?? '0');
      const memMatch = memStr?.match(/([\d.]+)/);
      const memoryMb = memMatch ? parseFloat(memMatch[1]) : 0;
      
      return {
        cpuPercent,
        memoryMb,
        pid: 0,  // Docker doesn't expose container PID easily
        uptimeSeconds: Math.floor((Date.now() - this.createdAt) / 1000),
      };
    } catch {
      return { cpuPercent: 0, memoryMb: 0, pid: 0, uptimeSeconds: 0 };
    }
  }

  async stop(): Promise<void> {
    if (this.containerId) {
      try {
        execSync(`docker stop ${this.containerId}`, { timeout: 5000 });
      } catch {}
      this.containerId = null;
      this.active = false;
    }
  }

  async kill(): Promise<void> {
    if (this.containerId) {
      try {
        execSync(`docker kill ${this.containerId}`, { timeout: 3000 });
      } catch {}
      this.containerId = null;
      this.active = false;
    }
  }
}
