/**
 * Workflow definitions for multi-agent orchestration.
 * 
 * A workflow is a sequence of tasks executed by agents.
 * Supports:
 *   - Sequential execution (task -> task -> task)
 *   - Parallel execution (task1 || task2 || task3)
 *   - Conditional branching (if result X, do Y)
 *   - Agent routing (assign based on capability)
 */

import type { AgentCapability, AgentTask, AgentResult } from '../agent/types.js';

export type WorkflowStepType = 'sequential' | 'parallel' | 'conditional' | 'agent_select';

export interface WorkflowStep {
  id: string;
  type: WorkflowStepType;
  /** Task description for this step */
  prompt: string;
  /** Required agent capabilities */
  requiredCapabilities?: AgentCapability[];
  /** For sequential: run after these steps complete */
  dependsOn?: string[];
  /** For conditional: condition function name */
  condition?: string;
  /** For conditional: branches */
  branches?: Record<string, WorkflowStep[]>;
  /** Output mapping: map result from previous step to this step's input */
  inputMapping?: Record<string, string>;
  /** Timeout in seconds */
  timeout?: number;
}

export interface WorkflowDefinition {
  id: string;
  name: string;
  description: string;
  version: string;
  steps: WorkflowStep[];
  /** Global timeout in seconds */
  timeout?: number;
  /** Error handling: 'stop' | 'continue' | 'retry' */
  onError?: 'stop' | 'continue' | 'retry';
  maxRetries?: number;
}

export interface WorkflowExecutionResult {
  workflowId: string;
  executionId: string;
  status: 'running' | 'completed' | 'failed' | 'timed_out';
  stepResults: Map<string, AgentResult>;
  startedAt: number;
  completedAt?: number;
  error?: string;
}

/**
 * Content creation workflow - generates a video/article from topic.
 */
export function createContentWorkflow(topic: string): WorkflowDefinition {
  return {
    id: 'content-creation-v1',
    name: 'Content Creation Pipeline',
    description: 'Multi-agent pipeline for creating content from topic',
    version: '1.0',
    onError: 'retry',
    maxRetries: 2,
    steps: [
      {
        id: 'research',
        type: 'sequential',
        prompt: `Research the topic: "${topic}". Find key facts, trends, and interesting angles.`,
        requiredCapabilities: ['web_search', 'data_analysis'],
      },
      {
        id: 'write_script',
        type: 'sequential',
        prompt: `Write a compelling script about "${topic}" based on the research provided.`,
        requiredCapabilities: ['content_writing'],
        dependsOn: ['research'],
        inputMapping: { research_result: 'research.output' },
      },
      {
        id: 'generate_assets',
        type: 'parallel',
        prompt: 'Create visual assets and code snippets for the content.',
        requiredCapabilities: ['code_generation', 'image_analysis'],
        dependsOn: ['write_script'],
      },
      {
        id: 'review',
        type: 'sequential',
        prompt: 'Review the generated content for quality, accuracy, and engagement.',
        requiredCapabilities: ['content_writing'],
        dependsOn: ['generate_assets'],
        inputMapping: { script: 'write_script.output', assets: 'generate_assets.output' },
      },
      {
        id: 'publish',
        type: 'sequential',
        prompt: 'Prepare the final content package for publishing.',
        requiredCapabilities: ['file_operations'],
        dependsOn: ['review'],
      },
    ],
  };
}

/**
 * Software development workflow - builds a feature from specification.
 */
export function createDevelopmentWorkflow(spec: string): WorkflowDefinition {
  return {
    id: 'dev-workflow-v1',
    name: 'Software Development Pipeline',
    description: 'Multi-agent pipeline for building software features',
    version: '1.0',
    onError: 'stop',
    steps: [
      {
        id: 'analyze',
        type: 'sequential',
        prompt: `Analyze this specification: "${spec}". Break it down into tasks.`,
        requiredCapabilities: ['data_analysis'],
      },
      {
        id: 'implement',
        type: 'parallel',
        prompt: 'Implement the code based on the analysis.',
        requiredCapabilities: ['code_generation'],
        dependsOn: ['analyze'],
      },
      {
        id: 'review_code',
        type: 'sequential',
        prompt: 'Review the implemented code for bugs, security issues, and quality.',
        requiredCapabilities: ['code_generation'],
        dependsOn: ['implement'],
      },
      {
        id: 'test',
        type: 'sequential',
        prompt: 'Write and run tests for the implemented code.',
        requiredCapabilities: ['code_generation', 'shell_commands'],
        dependsOn: ['review_code'],
      },
    ],
  };
}
