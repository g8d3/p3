/**
 * Agent type definitions.
 */

export type AgentStatus = 'idle' | 'running' | 'blocked' | 'error' | 'completed' | 'killed';

export type AgentCapability = 
  | 'code_generation'
  | 'content_writing'
  | 'web_search'
  | 'browser_automation'
  | 'file_operations'
  | 'shell_commands'
  | 'image_analysis'
  | 'video_editing'
  | 'data_analysis'
  | 'translation';

export interface AgentConfig {
  /** Unique agent ID */
  id: string;
  /** Human-readable name */
  name: string;
  /** LLM provider/model to use */
  model: string;
  /** System prompt / persona */
  systemPrompt?: string;
  /** Agent capabilities */
  capabilities: AgentCapability[];
  /** Resource limits */
  memoryLimitMb?: number;
  cpuLimit?: number;
  /** Sandbox config */
  sandbox?: {
    provider: string;
    networkEnabled: boolean;
    timeoutSeconds: number;
  };
}

export interface AgentTask {
  /** Unique task ID */
  id: string;
  /** Agent assigned to this task */
  agentId: string;
  /** Task description/prompt */
  prompt: string;
  /** Input context (files, URLs, etc.) */
  context?: Record<string, unknown>;
  /** Expected output format */
  outputFormat?: 'text' | 'json' | 'file' | 'code' | 'video';
  /** Priority (higher = more urgent) */
  priority: number;
  /** Task deadline */
  deadline?: Date;
  /** Dependencies (task IDs that must complete first) */
  dependsOn?: string[];
  /** Created timestamp */
  createdAt: Date;
}

export interface AgentResult {
  /** Task ID */
  taskId: string;
  /** Agent ID */
  agentId: string;
  /** Status */
  status: 'success' | 'failure' | 'timeout' | 'error';
  /** Output text */
  output: string;
  /** Output files (paths inside sandbox) */
  outputFiles?: string[];
  /** Token usage */
  tokenUsage?: {
    prompt: number;
    completion: number;
    total: number;
  };
  /** Duration */
  durationMs: number;
  /** Error message if failed */
  error?: string;
  /** Created timestamp */
  createdAt: Date;
}

export interface AgentMetrics {
  agentId: string;
  tasksCompleted: number;
  tasksFailed: number;
  totalTokensUsed: number;
  totalDurationMs: number;
  averageTokensPerTask: number;
  averageDurationMs: number;
  currentStatus: AgentStatus;
  cpuPercent: number;
  memoryMb: number;
  uptimeSeconds: number;
}
