/**
 * Sandbox module - pluggable isolation backends for AI agents.
 * 
 * Architecture:
 *   SandboxProvider (interface) ─┬─ DockerSandbox    (immediate, dev)
 *                                ├─ CubeSandbox      (KVM, production)
 *                                ├─ MicroSandbox     (Rust, TODO)
 *                                └─ AgentOS          (V8 isolates, TODO)
 * 
 * Each provider creates SandboxInstances with resource limits,
 * file I/O, and command execution.
 * 
 * Priority: CubeSandbox > DockerSandbox
 *   - CubeSandbox requires CubeAPI running on localhost:3000
 *   - DockerSandbox requires Docker on the host
 *   - If neither is available, system warns and proceeds without isolation
 */

import type { SandboxProvider } from './interface.js';
import { DockerSandboxProvider } from './docker-sandbox.js';
import { CubeSandboxProvider } from './cubesandbox-provider.js';

export type { SandboxProvider, SandboxInstance, SandboxConfig, SandboxMetrics, CommandResult } from './interface.js';
export { SandboxError } from './interface.js';
export { DockerSandboxProvider } from './docker-sandbox.js';
export { CubeSandboxProvider } from './cubesandbox-provider.js';

/**
 * Auto-detect the best available sandbox provider.
 * Checks CubeSandbox first (KVM, production), then Docker (dev).
 */
export async function getBestProvider(): Promise<SandboxProvider> {
  const providers: SandboxProvider[] = [
    new CubeSandboxProvider(),      // KVM-level, <5MB/agent
    new DockerSandboxProvider(),     // Namespace-level, dev fallback
  ];
  
  for (const p of providers) {
    if (await p.isAvailable()) {
      console.log(`[sandbox] Using provider: ${p.name}`);
      const info = await p.getInfo();
      console.log(`[sandbox]   version: ${info.version}`);
      console.log(`[sandbox]   features: ${info.features.join(', ')}`);
      return p;
    }
  }
  
  // No provider available - warn and proceed without isolation
  console.warn('[sandbox] ⚠ No sandbox provider available! Install Docker or CubeSandbox.');
  console.warn('[sandbox]   Docker:     docker.io');
  console.warn('[sandbox]   CubeSandbox: https://github.com/TencentCloud/CubeSandbox');
  // Return Docker anyway (will fail gracefully later)
  return new DockerSandboxProvider();
}
