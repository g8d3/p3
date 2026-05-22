/**
 * Multi-agent orchestrator.
 * 
 * Coordinates multiple agents to execute workflows.
 * Uses:
 *   - AgentManager for agent lifecycle
 *   - TaskQueue for scheduling with dependencies
 *   - Workflow definitions for multi-step pipelines
 *   - ContextWindowManager for context management
 *   - EpisodicMemory for persistence
 */

import { AgentManager } from '../agent/manager.js';
import { ContextWindowManager, EpisodicMemory } from '../memory/index.js';
import type { SandboxProvider } from '../sandbox/index.js';
import { TaskQueue } from './task-queue.js';
import type { WorkflowDefinition, WorkflowStep, WorkflowExecutionResult } from './workflow.js';
import type { AgentTask, AgentResult, AgentCapability } from '../agent/types.js';
import { randomUUID } from 'node:crypto';

export class Orchestrator {
  readonly agentManager: AgentManager;
  readonly memory: EpisodicMemory;
  readonly contextWindow: ContextWindowManager;
  private taskQueue: TaskQueue;
  private workflows: Map<string, WorkflowDefinition> = new Map();
  private executions: Map<string, WorkflowExecutionResult> = new Map();
  private running = false;

  constructor(sandboxProvider: SandboxProvider) {
    this.agentManager = new AgentManager(sandboxProvider);
    this.memory = new EpisodicMemory('./data');
    this.contextWindow = new ContextWindowManager();
    this.taskQueue = new TaskQueue();
  }

  /**
   * Register a workflow definition.
   */
  registerWorkflow(workflow: WorkflowDefinition): void {
    this.workflows.set(workflow.id, workflow);
  }

  /**
   * Execute a workflow.
   */
  async executeWorkflow(workflowId: string, context?: Record<string, unknown>): Promise<WorkflowExecutionResult> {
    const workflow = this.workflows.get(workflowId);
    if (!workflow) throw new Error(`Workflow not found: ${workflowId}`);

    const executionId = `exec-${randomUUID().slice(0, 8)}`;
    const execution: WorkflowExecutionResult = {
      workflowId,
      executionId,
      status: 'running',
      stepResults: new Map(),
      startedAt: Date.now(),
    };
    this.executions.set(executionId, execution);
    
    const sessionId = this.memory.createSession(`workflow-${workflowId}`);
    this.memory.recordEvent(sessionId, 'task_start', { workflowId, executionId });

    try {
      // Process each step
      for (const step of workflow.steps) {
        const stepResult = await this.executeStep(step, workflow, execution);
        execution.stepResults.set(step.id, stepResult);
        
        // Record event
        this.memory.recordEvent(sessionId, 'task_end', {
          stepId: step.id,
          status: stepResult.status,
          durationMs: stepResult.durationMs,
        });

        if (stepResult.status !== 'success' && workflow.onError === 'stop') {
          execution.status = 'failed';
          execution.error = `Step ${step.id} failed: ${stepResult.error}`;
          break;
        }
      }

      if (execution.status === 'running') {
        execution.status = 'completed';
        execution.completedAt = Date.now();
      }
      
      this.memory.endSession(sessionId, `Workflow ${workflowId} ${execution.status}`);
    } catch (err: any) {
      execution.status = 'failed';
      execution.error = err.message;
      execution.completedAt = Date.now();
      this.memory.recordEvent(sessionId, 'error', { message: err.message });
      this.memory.endSession(sessionId, `Workflow ${workflowId} failed: ${err.message}`);
    }

    return execution;
  }

  private async executeStep(
    step: WorkflowStep,
    workflow: WorkflowDefinition,
    execution: WorkflowExecutionResult
  ): Promise<AgentResult> {
    // Find agent with required capabilities
    const agents = this.agentManager.listAgents();
    const candidates = step.requiredCapabilities?.length
      ? agents.filter(a => step.requiredCapabilities!.every(c => a.capabilities.includes(c)))
      : agents;
    
    if (candidates.length === 0) {
      return {
        taskId: '',
        agentId: '',
        status: 'error',
        output: '',
        durationMs: 0,
        error: `No agent available with capabilities: ${step.requiredCapabilities?.join(', ')}`,
        createdAt: new Date(),
      };
    }

    const agent = candidates[0]; // Simple round-robin: pick first available
    
    // Build task
    const task = {
      prompt: step.prompt,
      priority: 1,
    };

    // Execute
    return this.agentManager.executeTask(agent.id, task);
  }

  /**
   * Get execution result.
   */
  getExecution(executionId: string): WorkflowExecutionResult | undefined {
    return this.executions.get(executionId);
  }

  /**
   * Start the orchestrator loop (processes queued tasks).
   */
  start(): void {
    this.running = true;
    this.processLoop();
  }

  stop(): void {
    this.running = false;
  }

  private async processLoop(): Promise<void> {
    while (this.running) {
      const task = this.taskQueue.next();
      if (task) {
        // Find appropriate agent and execute asynchronously
        this.executeTaskAsync(task).catch(console.error);
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  private async executeTaskAsync(task: AgentTask): Promise<void> {
    const agents = this.agentManager.listAgents();
    if (agents.length === 0) {
      console.error('[orchestrator] No agents registered');
      return;
    }
    
    const result = await this.agentManager.executeTask(agents[0].id, {
      prompt: task.prompt,
      priority: task.priority,
    });
    
    this.taskQueue.complete(task.id, result);
  }

  /**
   * Cleanup resources.
   */
  async shutdown(): Promise<void> {
    this.stop();
    await this.agentManager.stopAll();
    this.memory.close();
  }
}
