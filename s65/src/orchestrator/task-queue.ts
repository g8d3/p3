/**
 * Task queue with priority scheduling.
 * 
 * Design:
 *   - Priority queue (binary heap)
 *   - Dependency tracking
 *   - Task timeout handling
 *   - Retry logic
 *   - Status tracking
 */

import type { AgentTask, AgentResult } from '../agent/types.js';

type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'blocked';

interface QueuedTask extends AgentTask {
  status: TaskStatus;
  retryCount: number;
  maxRetries: number;
  result?: AgentResult;
  blockedBy: string[];
}

export class TaskQueue {
  private tasks: Map<string, QueuedTask> = new Map();
  private readyQueue: QueuedTask[] = [];
  private processing = false;

  /**
   * Add a task to the queue.
   */
  add(task: AgentTask, maxRetries = 2): void {
    const blockedBy = (task.dependsOn ?? [])
      .filter(depId => this.tasks.has(depId));
    
    const queued: QueuedTask = {
      ...task,
      status: blockedBy.length > 0 ? 'blocked' : 'pending',
      retryCount: 0,
      maxRetries,
      blockedBy,
    };
    
    this.tasks.set(task.id, queued);
    
    if (queued.status === 'pending') {
      this.readyQueue.push(queued);
      this.readyQueue.sort((a, b) => b.priority - a.priority);
    }
  }

  /**
   * Get the next ready task.
   */
  next(): AgentTask | null {
    const task = this.readyQueue.shift();
    if (task) {
      task.status = 'running';
      return task;
    }
    return null;
  }

  /**
   * Mark a task as completed and resolve dependents.
   */
  complete(taskId: string, result: AgentResult): void {
    const task = this.tasks.get(taskId);
    if (!task) return;
    
    task.status = result.status === 'success' ? 'completed' : 'failed';
    task.result = result;
    
    // Resolve dependencies
    if (result.status === 'success') {
      for (const [, t] of this.tasks) {
        if (t.status === 'blocked') {
          t.blockedBy = t.blockedBy.filter(id => id !== taskId);
          if (t.blockedBy.length === 0) {
            t.status = 'pending';
            this.readyQueue.push(t);
            this.readyQueue.sort((a, b) => b.priority - a.priority);
          }
        }
      }
    } else {
      // Failed - check for retry
      if (task.retryCount < task.maxRetries) {
        task.retryCount++;
        task.status = 'pending';
        this.readyQueue.push(task);
        this.readyQueue.sort((a, b) => b.priority - a.priority);
      }
    }
  }

  /**
   * Get task status.
   */
  getStatus(taskId: string): TaskStatus | null {
    return this.tasks.get(taskId)?.status ?? null;
  }

  /**
   * Get all tasks.
   */
  getAll(): QueuedTask[] {
    return Array.from(this.tasks.values());
  }

  /**
   * Get pending count.
   */
  get pendingCount(): number {
    return this.readyQueue.length;
  }

  /**
   * Check if all tasks are done.
   */
  get isComplete(): boolean {
    return Array.from(this.tasks.values()).every(t => 
      ['completed', 'failed', 'cancelled'].includes(t.status)
    );
  }

  /**
   * Get stats.
   */
  getStats(): { pending: number; running: number; completed: number; failed: number; blocked: number } {
    const stats = { pending: 0, running: 0, completed: 0, failed: 0, blocked: 0 };
    for (const t of this.tasks.values()) {
      stats[t.status as keyof typeof stats]++;
    }
    return stats;
  }
}
