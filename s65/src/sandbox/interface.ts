/**
 * Sandbox abstraction layer.
 * 
 * SandboxProvider is the pluggable backend for running agents in isolation.
 * Multiple implementations:
 *   - DockerSandbox   (immediate, from s50)
 *   - CubeSandbox     (KVM-level, most efficient <5MB/agent)
 *   - MicroSandbox    (Rust-based sandbox)
 *   - AgentOS         (V8 isolates, ~6ms coldstarts)
 */

export interface SandboxConfig {
  /** Memory limit in MB */
  memoryLimitMb?: number;
  /** CPU cores limit */
  cpuLimit?: number;
  /** Enable network access */
  networkEnabled?: boolean;
  /** Timeout in seconds before killing the sandbox */
  timeoutSeconds?: number;
  /** Environment variables */
  env?: Record<string, string>;
  /** Working directory inside sandbox */
  workdir?: string;
  /** Image/template to use */
  image?: string;
}

export interface SandboxMetrics {
  /** CPU usage in % */
  cpuPercent: number;
  /** Memory usage in MB */
  memoryMb: number;
  /** Process ID */
  pid: number;
  /** Uptime in seconds */
  uptimeSeconds: number;
}

export interface SandboxProvider {
  /** Unique name for this provider */
  readonly name: string;
  
  /** Create a new sandbox */
  create(config?: SandboxConfig): Promise<SandboxInstance>;
  
  /** Check if this provider is available on the system */
  isAvailable(): Promise<boolean>;
  
  /** Get provider info */
  getInfo(): Promise<{ version: string; features: string[] }>;
}

export interface SandboxInstance {
  /** Unique sandbox ID */
  readonly id: string;
  
  /** Provider that created this sandbox */
  readonly provider: SandboxProvider;
  
  /** Execute a command inside the sandbox */
  exec(command: string, args?: string[]): Promise<CommandResult>;
  
  /** Execute a command with streaming output */
  execStream(command: string, args?: string[], onData?: (chunk: string) => void): Promise<CommandResult>;
  
  /** Write a file to the sandbox */
  writeFile(path: string, content: string | Buffer): Promise<void>;
  
  /** Read a file from the sandbox */
  readFile(path: string): Promise<Buffer>;
  
  /** Get resource usage metrics */
  getMetrics(): Promise<SandboxMetrics>;
  
  /** Stop the sandbox */
  stop(): Promise<void>;
  
  /** Force kill the sandbox */
  kill(): Promise<void>;
}

export interface CommandResult {
  exitCode: number;
  stdout: string;
  stderr: string;
  durationMs: number;
}

export class SandboxError extends Error {
  constructor(message: string, public readonly cause?: Error) {
    super(message);
    this.name = 'SandboxError';
  }
}
