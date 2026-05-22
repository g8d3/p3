#!/usr/bin/env tsx
/**
 * P3 Agent System - Efficient Multi-Agent Platform
 * 
 * Entry point. Initializes the core components:
 *   1. Sandbox provider (auto-detected)
 *   2. Orchestrator with agent manager
 *   3. Memory systems (context window, episodic)
 *   4. Dashboard server
 *   5. Content pipeline
 * 
 * Usage:
 *   npx tsx src/index.ts                    # Start with dashboard
 *   npx tsx src/index.ts --no-dashboard      # Headless mode
 *   npx tsx src/index.ts --example           # Run example workflow
 */

import { getBestProvider } from './sandbox/index.js';
import { Orchestrator } from './orchestrator/index.js';
import { DashboardServer } from './dashboard/server.js';
import { ContentPipeline } from './content/pipeline.js';
import { telemetry } from './monitor/telemetry.js';
import { createContentWorkflow, createDevelopmentWorkflow } from './orchestrator/workflow.js';

async function main() {
  const args = process.argv.slice(2);
  const noDashboard = args.includes('--no-dashboard');
  const runExample = args.includes('--example');

  console.log('');
  console.log('╔══════════════════════════════════════════════╗');
  console.log('║       P3 Agent System v0.1.0                ║');
  console.log('║   Efficient Multi-Agent Platform             ║');
  console.log('╚══════════════════════════════════════════════╝');
  console.log('');

  // 1. Initialize sandbox
  console.log('[init] Detecting sandbox provider...');
  const sandboxProvider = await getBestProvider();
  const providerInfo = await sandboxProvider.getInfo();
  console.log(`[init] Provider: ${sandboxProvider.name} v${providerInfo.version}`);

  // 2. Initialize orchestrator
  console.log('[init] Starting orchestrator...');
  const orchestrator = new Orchestrator(sandboxProvider);
  
  // Register default workflows
  orchestrator.registerWorkflow(createContentWorkflow('default'));
  orchestrator.registerWorkflow(createDevelopmentWorkflow('default'));
  
  orchestrator.start();

  // 3. Initialize content pipeline
  const contentPipeline = new ContentPipeline(orchestrator.agentManager);
  
  // 4. Register example agents
  const writer = orchestrator.agentManager.register({
    name: 'Writer',
    model: 'auto',
    capabilities: ['content_writing', 'web_search'],
    systemPrompt: 'You are an expert content creator. Write engaging, well-researched content.',
    memoryLimitMb: 256,
  });
  
  const coder = orchestrator.agentManager.register({
    name: 'Coder',
    model: 'auto',
    capabilities: ['code_generation', 'file_operations', 'shell_commands'],
    systemPrompt: 'You are an expert software engineer. Write clean, efficient, well-tested code.',
    memoryLimitMb: 512,
  });

  const analyst = orchestrator.agentManager.register({
    name: 'Analyst',
    model: 'auto',
    capabilities: ['data_analysis', 'web_search'],
    systemPrompt: 'You are an expert data analyst. Find insights and patterns in data.',
    memoryLimitMb: 256,
  });

  console.log(`[init] Registered ${orchestrator.agentManager.listAgents().length} agents`);

  // 5. Start telemetry
  telemetry.startSampling(5000);

  // 6. Start dashboard (unless headless mode)
  if (!noDashboard) {
    const dashboardPort = parseInt(process.env.DASHBOARD_PORT ?? '3030');
    const dashboard = new DashboardServer({
      port: dashboardPort,
      orchestrator,
    });
    await dashboard.start();
    
    // Keep process alive
    process.on('SIGINT', async () => {
      console.log('\n[shutdown] Cleaning up...');
      await orchestrator.shutdown();
      telemetry.close();
      process.exit(0);
    });
    
    console.log('\n[init] System ready!');
    console.log(`   Dashboard: http://localhost:${dashboardPort}`);
    console.log('   Press Ctrl+C to stop\n');
  }

  // 7. Run example if requested
  if (runExample) {
    console.log('[example] Running content creation workflow...');
    const contentResult = await contentPipeline.create({
      type: 'article',
      topic: 'The future of AI agents in software development',
      targetAudience: 'developers',
      tone: 'professional',
      length: 'short',
    });
    console.log(`[example] Content created in ${contentResult.durationMs}ms`);
    console.log(`[example] Tokens used: ${contentResult.tokensUsed}`);
    console.log(`[example] Content length: ${contentResult.content.length} chars`);
  }
}

main().catch((err) => {
  console.error('[fatal]', err);
  process.exit(1);
});
