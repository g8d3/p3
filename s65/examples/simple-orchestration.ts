#!/usr/bin/env tsx
/**
 * Example: Simple orchestration of multiple agents.
 * 
 * Shows:
 *   1. Registering agents with different capabilities
 *   2. Creating a workflow
 *   3. Executing tasks
 *   4. Monitoring results
 */

import { getBestProvider } from '../src/sandbox/index.js';
import { Orchestrator } from '../src/orchestrator/index.js';
import { createDevelopmentWorkflow } from '../src/orchestrator/workflow.js';

async function example() {
  console.log('=== P3 Multi-Agent Example ===\n');

  // 1. Initialize system
  const sandbox = await getBestProvider();
  const orchestrator = new Orchestrator(sandbox);

  // 2. Register agents with specific capabilities
  orchestrator.agentManager.register({
    name: 'Frontend Dev',
    model: 'auto',
    capabilities: ['code_generation'],
    systemPrompt: 'You are a senior frontend developer. Build clean, responsive UIs.',
    memoryLimitMb: 256,
    cpuLimit: 1,
  });

  orchestrator.agentManager.register({
    name: 'Backend Dev',
    model: 'auto',
    capabilities: ['code_generation', 'shell_commands'],
    systemPrompt: 'You are a senior backend developer. Build robust, scalable APIs.',
    memoryLimitMb: 512,
    cpuLimit: 1,
  });

  orchestrator.agentManager.register({
    name: 'Reviewer',
    model: 'auto',
    capabilities: ['code_generation', 'data_analysis'],
    systemPrompt: 'You are a code reviewer. Find bugs and suggest improvements.',
    memoryLimitMb: 256,
    cpuLimit: 1,
  });

  console.log(`Registered ${orchestrator.agentManager.listAgents().length} agents\n`);

  // 3. Register a workflow
  const workflow = createDevelopmentWorkflow('Build a REST API for a todo app with Express.js and SQLite');
  orchestrator.registerWorkflow(workflow);
  console.log(`Registered workflow: ${workflow.name}\n`);

  // 4. Execute a simple task on one agent
  console.log('Executing task on Frontend Dev...');
  const result = await orchestrator.agentManager.executeTask(
    orchestrator.agentManager.listAgents()[0].id,
    {
      prompt: 'Write a simple React component that displays a counter with increment/decrement buttons.',
      priority: 1,
    }
  );

  console.log(`  Status: ${result.status}`);
  console.log(`  Duration: ${result.durationMs}ms`);
  console.log(`  Tokens: ${result.tokenUsage?.total ?? '?'}`);
  console.log(`  Output: ${result.output.slice(0, 200)}...\n`);

  // 5. Show agent metrics
  const metrics = await orchestrator.agentManager.getMetrics(
    orchestrator.agentManager.listAgents()[0].id
  );
  console.log('Agent Metrics:');
  console.log(`  Tasks completed: ${metrics.tasksCompleted}`);
  console.log(`  Avg duration: ${metrics.averageDurationMs}ms`);
  console.log(`  Avg tokens/task: ${metrics.averageTokensPerTask}`);

  // 6. Cleanup
  await orchestrator.shutdown();
  console.log('\nDone!');
}

example().catch(console.error);
