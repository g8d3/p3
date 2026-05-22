/**
 * Telemetry system.
 * 
 * Tracks resource usage across all agents and sandboxes.
 * Provides real-time metrics for the dashboard.
 */

import { EventEmitter } from 'node:events';

interface TelemetryEvent {
  timestamp: number;
  type: 'agent_metrics' | 'sandbox_metrics' | 'task_result' | 'error' | 'workflow_event';
  data: Record<string, unknown>;
}

export class Telemetry extends EventEmitter {
  private events: TelemetryEvent[] = [];
  private maxEvents = 10_000;
  private samplingInterval: ReturnType<typeof setInterval> | null = null;
  private subscriptions: Map<string, Set<(event: TelemetryEvent) => void>> = new Map();

  constructor() {
    super();
    this.setMaxListeners(100);
  }

  /**
   * Record a telemetry event.
   */
  record(type: TelemetryEvent['type'], data: Record<string, unknown>): void {
    const event: TelemetryEvent = {
      timestamp: Date.now(),
      type,
      data,
    };
    
    this.events.push(event);
    
    // Trim if over limit
    if (this.events.length > this.maxEvents) {
      this.events = this.events.slice(-this.maxEvents / 2);
    }
    
    // Emit to listeners
    this.emit(type, event);
    this.emit('*', event);
    
    // Notify registered subscriptions
    const typeSubs = this.subscriptions.get(type);
    if (typeSubs) {
      typeSubs.forEach(cb => cb(event));
    }
    const allSubs = this.subscriptions.get('*');
    if (allSubs) {
      allSubs.forEach(cb => cb(event));
    }
  }

  /**
   * Subscribe to events.
   */
  subscribe(type: string, callback: (event: TelemetryEvent) => void): () => void {
    if (!this.subscriptions.has(type)) {
      this.subscriptions.set(type, new Set());
    }
    this.subscriptions.get(type)!.add(callback);
    
    return () => {
      this.subscriptions.get(type)?.delete(callback);
    };
  }

  /**
   * Get recent events.
   */
  getRecent(limit = 100, type?: TelemetryEvent['type']): TelemetryEvent[] {
    const filtered = type 
      ? this.events.filter(e => e.type === type)
      : this.events;
    return filtered.slice(-limit);
  }

  /**
   * Get stats summary.
   */
  getSummary(): Record<string, unknown> {
    const typeCounts: Record<string, number> = {};
    for (const e of this.events) {
      typeCounts[e.type] = (typeCounts[e.type] ?? 0) + 1;
    }
    
    return {
      totalEvents: this.events.length,
      byType: typeCounts,
      timeRange: {
        start: this.events[0]?.timestamp,
        end: this.events[this.events.length - 1]?.timestamp,
      },
    };
  }

  /**
   * Start periodic sampling of agent metrics.
   */
  startSampling(intervalMs = 5000): void {
    if (this.samplingInterval) return;
    
    this.samplingInterval = setInterval(() => {
      this.record('agent_metrics', {
        timestamp: Date.now(),
        agents: {},
      });
    }, intervalMs);
  }

  stopSampling(): void {
    if (this.samplingInterval) {
      clearInterval(this.samplingInterval);
      this.samplingInterval = null;
    }
  }

  close(): void {
    this.stopSampling();
    this.removeAllListeners();
    this.subscriptions.clear();
  }
}

// Singleton
export const telemetry = new Telemetry();
