/**
 * CubeSandbox Sandbox Provider.
 * 
 * Implements SandboxProvider using CubeSandbox's E2B-compatible API.
 * 
 * Architecture:
 *   - Connects to CubeAPI (REST API, port 3000 by default)
 *   - Creates sandbox environments via E2B protocol
 *   - Executes commands inside sandboxes
 *   - Manages sandbox lifecycle
 * 
 * CubeSandbox is a KVM-based sandbox from Tencent Cloud:
 *   - Hardware-level isolation (dedicated kernel per sandbox)
 *   - <5MB per-instance memory overhead (CoW + stripped runtime)
 *   - <60ms cold start via snapshot cloning
 *   - E2B SDK compatible (drop-in replacement)
 * 
 * Requirements:
 *   - CubeSandbox cluster running (CubeMaster + Cubelet + CubeAPI)
 *   - Or dev-env (dev-env/run_vm.sh)
 */

import type { SandboxProvider, SandboxInstance, SandboxConfig, SandboxMetrics, CommandResult } from './interface.js';
import { SandboxError } from './interface.js';
import { randomUUID } from 'node:crypto';
import { request } from 'node:http';

const CUBE_API_DEFAULT = 'http://127.0.0.1:3000';

interface E2BSandbox {
  sandboxId: string;
  status: 'running' | 'stopped' | 'error';
  createdAt: string;
}

interface E2BExecution {
  exitCode: number;
  stdout: string;
  stderr: string;
  error?: string;
}

export class CubeSandboxProvider implements SandboxProvider {
  readonly name = 'cubesandbox';
  private apiUrl: string;
  private healthy = false;

  constructor(apiUrl?: string) {
    this.apiUrl = apiUrl ?? process.env.CUBE_API_URL ?? CUBE_API_DEFAULT;
  }

  async isAvailable(): Promise<boolean> {
    try {
      const response = await fetch(`${this.apiUrl}/health`, {
        signal: AbortSignal.timeout(3000),
      });
      this.healthy = response.ok;
      return this.healthy;
    } catch {
      this.healthy = false;
      return false;
    }
  }

  async getInfo() {
    const health = await this.fetchJson('/health');
    return {
      version: health?.version ?? 'unknown',
      features: ['kvm-isolation', 'e2b-compatible', 'cow-memory', 'hardware-sandbox'],
    };
  }

  async create(config: SandboxConfig = {}): Promise<SandboxInstance> {
    if (!this.healthy) {
      const avail = await this.isAvailable();
      if (!avail) throw new SandboxError('CubeSandbox API not available at ' + this.apiUrl);
    }

    const id = `sb-${randomUUID().slice(0, 8)}`;
    const instance = new CubeSandboxInstance(id, this.apiUrl, config);
    await instance.init();
    return instance;
  }

  async fetchJson(path: string, options?: RequestInit): Promise<any> {
    const url = `${this.apiUrl}${path}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      signal: options?.signal ?? AbortSignal.timeout(10000),
    });
    if (!response.ok) {
      throw new SandboxError(`CubeAPI error ${response.status}: ${response.statusText}`);
    }
    return response.json();
  }

  async fetchText(path: string, options?: RequestInit): Promise<string> {
    const url = `${this.apiUrl}${path}`;
    const response = await fetch(url, {
      ...options,
      signal: options?.signal ?? AbortSignal.timeout(10000),
    });
    if (!response.ok) {
      throw new SandboxError(`CubeAPI error ${response.status}: ${response.statusText}`);
    }
    return response.text();
  }
}

class CubeSandboxInstance implements SandboxInstance {
  readonly id: string;
  readonly provider: CubeSandboxProvider;
  private config: SandboxConfig;
  private apiUrl: string;
  private e2bSandboxId: string | null = null;
  private createdAt: number;

  constructor(id: string, apiUrl: string, config: SandboxConfig) {
    this.id = id;
    this.provider = new CubeSandboxProvider(apiUrl);
    this.apiUrl = apiUrl;
    this.config = config;
    this.createdAt = Date.now();
  }

  async init(): Promise<void> {
    // Create sandbox via E2B API
    // E2B sandbox creation: POST /v1/sandboxes
    const body: Record<string, unknown> = {
      templateId: 'default',
      metadata: { sandboxId: this.id },
    };
    if (this.config.memoryLimitMb) body.memoryMb = this.config.memoryLimitMb;
    if (this.config.timeoutSeconds) body.timeoutMs = this.config.timeoutSeconds * 1000;

    const result = await this.provider.fetchJson('/v1/sandboxes', {
      method: 'POST',
      body: JSON.stringify(body),
    });

    this.e2bSandboxId = result.sandboxId ?? result.id;
    if (!this.e2bSandboxId) {
      throw new SandboxError('Failed to create CubeSandbox: no sandboxId in response');
    }
  }

  async exec(command: string, args?: string[]): Promise<CommandResult> {
    if (!this.e2bSandboxId) throw new SandboxError('Sandbox not initialized');

    const start = Date.now();
    const cmd = args ? `${command} ${args.join(' ')}` : command;

    // E2B code execution: POST /v1/sandboxes/{id}/execute
    const result: E2BExecution = await this.provider.fetchJson(
      `/v1/sandboxes/${this.e2bSandboxId}/execute`,
      {
        method: 'POST',
        body: JSON.stringify({ code: cmd, language: 'bash' }),
      }
    );

    return {
      exitCode: result.exitCode ?? 1,
      stdout: result.stdout ?? '',
      stderr: result.stderr ?? '',
      durationMs: Date.now() - start,
    };
  }

  async execStream(
    command: string,
    args?: string[],
    onData?: (chunk: string) => void
  ): Promise<CommandResult> {
    // For streaming, use the same exec but with onData callback
    const result = await this.exec(command, args);
    if (onData && result.stdout) {
      onData(result.stdout);
    }
    return result;
  }

  async writeFile(path: string, content: string | Buffer): Promise<void> {
    if (!this.e2bSandboxId) throw new SandboxError('Sandbox not initialized');
    const contentStr = Buffer.isBuffer(content) ? content.toString('base64') : Buffer.from(content).toString('base64');

    // E2B file write: POST /v1/sandboxes/{id}/files
    await this.provider.fetchJson(
      `/v1/sandboxes/${this.e2bSandboxId}/files`,
      {
        method: 'POST',
        body: JSON.stringify({ path, content: contentStr, encoding: 'base64' }),
      }
    );
  }

  async readFile(path: string): Promise<Buffer> {
    if (!this.e2bSandboxId) throw new SandboxError('Sandbox not initialized');

    // E2B file read: GET /v1/sandboxes/{id}/files/{path}
    const result = await this.provider.fetchJson(
      `/v1/sandboxes/${this.e2bSandboxId}/files/${encodeURIComponent(path)}`
    );

    const content = result.content ?? result.data ?? '';
    return Buffer.from(content, 'base64');
  }

  async getMetrics(): Promise<SandboxMetrics> {
    if (!this.e2bSandboxId) {
      return { cpuPercent: 0, memoryMb: 0, pid: 0, uptimeSeconds: 0 };
    }

    try {
      const info = await this.provider.fetchJson(`/v1/sandboxes/${this.e2bSandboxId}`);
      return {
        cpuPercent: info.cpuUsage ?? 0,
        memoryMb: info.memoryMb ?? 0,
        pid: 0, // KVM VMs don't expose host PID
        uptimeSeconds: Math.floor((Date.now() - this.createdAt) / 1000),
      };
    } catch {
      return { cpuPercent: 0, memoryMb: 0, pid: 0, uptimeSeconds: 0 };
    }
  }

  async stop(): Promise<void> {
    if (this.e2bSandboxId) {
      try {
        // E2B stop: POST /v1/sandboxes/{id}/stop
        await this.provider.fetchJson(
          `/v1/sandboxes/${this.e2bSandboxId}/stop`,
          { method: 'POST' }
        );
      } catch {}
      this.e2bSandboxId = null;
    }
  }

  async kill(): Promise<void> {
    if (this.e2bSandboxId) {
      try {
        // E2B kill: DELETE /v1/sandboxes/{id}
        await this.provider.fetchJson(
          `/v1/sandboxes/${this.e2bSandboxId}`,
          { method: 'DELETE' }
        );
      } catch {}
      this.e2bSandboxId = null;
    }
  }
}
