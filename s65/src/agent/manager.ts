/**
 * Agent lifecycle manager.
 * 
 * Manages creation, execution, monitoring, and cleanup of AI agents.
 * Each agent runs inside a sandbox with resource limits.
 * 
 * Key design decisions for efficiency:
 * 1. Agents are lazily spawned (only when they have work)
 * 2. Idle agents are terminated after configurable timeout
 * 3. Resource limits enforced at sandbox level
 * 4. Context window is managed externally (memory module)
 */

import { randomUUID } from 'node:crypto';
import type { SandboxProvider, SandboxInstance } from '../sandbox/interface.js';
import type { AgentConfig, AgentTask, AgentResult, AgentStatus, AgentMetrics, AgentCapability } from './types.js';

interface AgentInstance {
  config: AgentConfig;
  sandbox: SandboxInstance | null;
  status: AgentStatus;
  currentTask: AgentTask | null;
  createdAt: number;
  lastActiveAt: number;
  tasksCompleted: number;
  tasksFailed: number;
  totalTokensUsed: number;
  totalDurationMs: number;
}

export class AgentManager {
  private agents: Map<string, AgentInstance> = new Map();
  private sandboxProvider: SandboxProvider;
  private idleTimeoutMs: number;
  private cleanupInterval: ReturnType<typeof setInterval> | null = null;

  constructor(sandboxProvider: SandboxProvider, idleTimeoutMs = 300_000) {
    this.sandboxProvider = sandboxProvider;
    this.idleTimeoutMs = idleTimeoutMs;
    this.startCleanupLoop();
  }

  /**
   * Register a new agent configuration.
   */
  register(config: Partial<AgentConfig> & { name: string; model: string }): AgentConfig {
    const id = config.id || `agent-${randomUUID().slice(0, 8)}`;
    const fullConfig: AgentConfig = {
      id,
      name: config.name,
      model: config.model,
      systemPrompt: config.systemPrompt,
      capabilities: config.capabilities ?? [],
      memoryLimitMb: config.memoryLimitMb ?? 512,
      cpuLimit: config.cpuLimit ?? 1,
      sandbox: config.sandbox ?? {
        provider: 'docker',
        networkEnabled: false,
        timeoutSeconds: 3600,
      },
    };
    
    this.agents.set(id, {
      config: fullConfig,
      sandbox: null,
      status: 'idle',
      currentTask: null,
      createdAt: Date.now(),
      lastActiveAt: Date.now(),
      tasksCompleted: 0,
      tasksFailed: 0,
      totalTokensUsed: 0,
      totalDurationMs: 0,
    });
    
    return fullConfig;
  }

  /**
   * Execute a task on an agent.
   */
  async executeTask(agentId: string, task: Omit<AgentTask, 'id' | 'agentId' | 'createdAt'>): Promise<AgentResult> {
    const agent = this.agents.get(agentId);
    if (!agent) throw new Error(`Agent not found: ${agentId}`);
    
    const fullTask: AgentTask = {
      ...task,
      id: `task-${randomUUID().slice(0, 8)}`,
      agentId,
      createdAt: new Date(),
    };
    
    agent.status = 'running';
    agent.currentTask = fullTask;
    const startTime = Date.now();
    
    try {
      // Ensure sandbox is running
      if (!agent.sandbox) {
        agent.sandbox = await this.sandboxProvider.create({
          memoryLimitMb: agent.config.memoryLimitMb,
          cpuLimit: agent.config.cpuLimit,
          networkEnabled: agent.config.sandbox?.networkEnabled,
          timeoutSeconds: agent.config.sandbox?.timeoutSeconds,
        });
      }
      
      // Prepare the task prompt with system context
      const fullPrompt = [
        agent.config.systemPrompt,
        '',
        '## TASK',
        task.prompt,
        task.context ? `\n## CONTEXT\n${JSON.stringify(task.context, null, 2)}` : '',
      ].filter(Boolean).join('\n');
      
      // Write prompt to temp file, then exec it
      const promptPath = `/tmp/task_${fullTask.id}.txt`;
      await agent.sandbox.writeFile(promptPath, fullPrompt);
      const result = await agent.sandbox.exec('sh', ['-c', `cat '${promptPath}'`]);
      
      const durationMs = Date.now() - startTime;
      
      // Estimate token usage (very rough: ~4 chars per token)
      const totalChars = fullPrompt.length + result.stdout.length;
      const estimatedTokens = Math.ceil(totalChars / 4);
      
      agent.status = 'completed';
      agent.tasksCompleted++;
      agent.totalDurationMs += durationMs;
      agent.totalTokensUsed += estimatedTokens;
      agent.lastActiveAt = Date.now();
      
      return {
        taskId: fullTask.id,
        agentId,
        status: result.exitCode === 0 ? 'success' : 'failure',
        output: result.stdout,
        tokenUsage: {
          prompt: Math.ceil(fullPrompt.length / 4),
          completion: Math.ceil(result.stdout.length / 4),
          total: estimatedTokens,
        },
        durationMs,
        error: result.exitCode !== 0 ? result.stderr : undefined,
        createdAt: new Date(),
      };
    } catch (err: any) {
      const durationMs = Date.now() - startTime;
      agent.status = 'error';
      agent.tasksFailed++;
      agent.totalDurationMs += durationMs;
      
      return {
        taskId: fullTask.id,
        agentId,
        status: 'error',
        output: '',
        durationMs,
        error: err.message,
        createdAt: new Date(),
      };
    }
  }

  /**
   * Get agent metrics.
   */
  getMetrics(agentId: string): Promise<AgentMetrics> {
    const agent = this.agents.get(agentId);
    if (!agent) throw new Error(`Agent not found: ${agentId}`);
    
    return Promise.resolve({
      agentId,
      tasksCompleted: agent.tasksCompleted,
      tasksFailed: agent.tasksFailed,
      totalTokensUsed: agent.totalTokensUsed,
      totalDurationMs: agent.totalDurationMs,
      averageTokensPerTask: agent.tasksCompleted > 0 
        ? Math.round(agent.totalTokensUsed / agent.tasksCompleted) 
        : 0,
      averageDurationMs: agent.tasksCompleted > 0 
        ? Math.round(agent.totalDurationMs / agent.tasksCompleted) 
        : 0,
      currentStatus: agent.status,
      cpuPercent: 0,
      memoryMb: 0,
      uptimeSeconds: Math.floor((Date.now() - agent.createdAt) / 1000),
    });
  }

  /**
   * Get all registered agents.
   */
  listAgents(): AgentConfig[] {
    return Array.from(this.agents.values()).map(a => a.config);
  }

  /**
   * Get agents by capability.
   */
  getAgentsByCapability(capability: AgentCapability): AgentConfig[] {
    return Array.from(this.agents.values())
      .filter(a => a.config.capabilities.includes(capability))
      .map(a => a.config);
  }

  /**
   * Stop and cleanup a specific agent.
   */
  async stopAgent(agentId: string): Promise<void> {
    const agent = this.agents.get(agentId);
    if (!agent) return;
    
    if (agent.sandbox) {
      await agent.sandbox.kill();
      agent.sandbox = null;
    }
    agent.status = 'killed';
  }

  /**
   * Stop all agents and cleanup.
   */
  async stopAll(): Promise<void> {
    for (const [id] of this.agents) {
      await this.stopAgent(id);
    }
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
  }

  private startCleanupLoop(): void {
    this.cleanupInterval = setInterval(async () => {
      const now = Date.now();
      for (const [id, agent] of this.agents) {
        if (agent.status === 'idle' && agent.sandbox && (now - agent.lastActiveAt) > this.idleTimeoutMs) {
          console.log(`[agent] Reclaiming idle agent ${id} (idle for ${(now - agent.lastActiveAt) / 1000}s)`);
          await agent.sandbox.kill();
          agent.sandbox = null;
        }
      }
    }, 30_000); // check every 30s
  }
}
