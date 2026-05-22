/**
 * Content creation pipeline.
 * 
 * Framework for AI agents to create content (articles, videos, code).
 * Integrates with the orchestrator for multi-agent content production.
 * 
 * Pipeline stages:
 *   1. Research - gather info, fact-check
 *   2. Plan - outline, structure
 *   3. Create - generate content (writing, coding, media)
 *   4. Review - quality check, fact-check
 *   5. Polish - refine, format for output
 *   6. Publish - prepare for distribution
 */

import type { AgentManager } from '../agent/manager.js';
import type { AgentCapability } from '../agent/types.js';
import { telemetry } from '../monitor/telemetry.js';

export type ContentType = 'article' | 'code' | 'video_script' | 'social_post' | 'documentation';

export interface ContentRequest {
  type: ContentType;
  topic: string;
  targetAudience?: string;
  tone?: string;
  length?: 'short' | 'medium' | 'long';
  format?: string;
  referenceUrls?: string[];
  additionalContext?: Record<string, unknown>;
}

export interface ContentResult {
  content: string;
  type: ContentType;
  topic: string;
  generatedAt: Date;
  durationMs: number;
  stages: ContentStageResult[];
  tokensUsed: number;
}

interface ContentStageResult {
  name: string;
  status: 'success' | 'failure';
  output: string;
  durationMs: number;
}

export class ContentPipeline {
  private agentManager: AgentManager;

  constructor(agentManager: AgentManager) {
    this.agentManager = agentManager;
  }

  /**
   * Execute a content creation pipeline.
   */
  async create(request: ContentRequest): Promise<ContentResult> {
    const startTime = Date.now();
    const stages: ContentStageResult[] = [];
    let totalTokens = 0;
    let fullContent = '';

    // Stage 1: Research
    const researchPrompt = this.buildResearchPrompt(request);
    const researchResult = await this.runStage('research', researchPrompt, ['web_search', 'data_analysis']);
    stages.push(researchResult);
    totalTokens += this.estimateTokens(researchResult.output);

    // Stage 2: Create
    const createPrompt = this.buildCreatePrompt(request, researchResult.output);
    const createResult = await this.runStage('create', createPrompt, ['content_writing', 'code_generation']);
    stages.push(createResult);
    totalTokens += this.estimateTokens(createResult.output);
    fullContent = createResult.output;

    // Stage 3: Review (only if we have content)
    if (fullContent) {
      const reviewPrompt = `Review and improve this ${request.type} about "${request.topic}":\n\n${fullContent}\n\nProvide specific improvements for clarity, engagement, and accuracy.`;
      const reviewResult = await this.runStage('review', reviewPrompt, ['content_writing']);
      stages.push(reviewResult);
      totalTokens += this.estimateTokens(reviewResult.output);
    }

    // Stage 4: Polish
    const polishPrompt = `Polish and format this ${request.type} for ${request.targetAudience || 'general audience'}:\n\n${fullContent}`;
    const polishResult = await this.runStage('polish', polishPrompt, ['content_writing']);
    stages.push(polishResult);
    totalTokens += this.estimateTokens(polishResult.output);
    
    if (polishResult.status === 'success') {
      fullContent = polishResult.output;
    }

    const durationMs = Date.now() - startTime;

    telemetry.record('workflow_event', {
      type: 'content_created',
      contentType: request.type,
      topic: request.topic,
      durationMs,
      tokensUsed: totalTokens,
      stages: stages.length,
    });

    return {
      content: fullContent,
      type: request.type,
      topic: request.topic,
      generatedAt: new Date(),
      durationMs,
      stages,
      tokensUsed: totalTokens,
    };
  }

  private async runStage(
    name: string,
    prompt: string,
    capabilities: AgentCapability[]
  ): Promise<ContentStageResult> {
    const start = Date.now();
    
    // Find agent with required capabilities
    const agents = this.agentManager.getAgentsByCapability(capabilities[0]);
    if (agents.length === 0) {
      return { name, status: 'failure', output: `No agent with ${capabilities[0]} capability`, durationMs: 0 };
    }
    
    try {
      const result = await this.agentManager.executeTask(agents[0].id, { prompt, priority: 1 });
      return {
        name,
        status: result.status === 'success' ? 'success' : 'failure',
        output: result.output,
        durationMs: Date.now() - start,
      };
    } catch (err: any) {
      return { name, status: 'failure', output: err.message, durationMs: Date.now() - start };
    }
  }

  private buildResearchPrompt(request: ContentRequest): string {
    return JSON.stringify({
      task: 'research',
      topic: request.topic,
      instructions: `Research the topic "${request.topic}" thoroughly. Find key facts, statistics, expert opinions, and recent developments.`,
      outputFormat: 'structured research brief with key findings, sources, and angles',
    });
  }

  private buildCreatePrompt(request: ContentRequest, research: string): string {
    return JSON.stringify({
      task: 'create_content',
      type: request.type,
      topic: request.topic,
      audience: request.targetAudience || 'general',
      tone: request.tone || 'professional',
      length: request.length || 'medium',
      research,
      instructions: `Create a ${request.length || 'medium'}-length ${request.type} about "${request.topic}" for ${request.targetAudience || 'a general audience'}. Use the research provided.`,
    });
  }

  private estimateTokens(text: string): number {
    return Math.ceil(text.length / 4);
  }
}
