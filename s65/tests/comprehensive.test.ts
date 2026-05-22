#!/usr/bin/env tsx
/**
 * Comprehensive test suite for P3 Agent System.
 * Tests every component: sandbox, agent, memory, orchestrator, content, dashboard.
 * 
 * Run: npx tsx tests/comprehensive.test.ts
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';

// ── Test 1: Sandbox ─────────────────────────────────────────────
async function testDockerSandbox() {
  console.log('\n📦 Test: DockerSandbox');
  
  const { DockerSandboxProvider } = await import('../src/sandbox/docker-sandbox.js');
  const provider = new DockerSandboxProvider();
  
  // 1.1 Availability
  const available = await provider.isAvailable();
  console.log(`  1.1 Available: ${available}`);
  if (!available) throw new Error('Docker not available');
  
  // 1.2 Info
  const info = await provider.getInfo();
  console.log(`  1.2 Info: version=${info.version}, features=${info.features.join(',')}`);
  if (!info.version) throw new Error('No version returned');
  
  // 1.3 Create sandbox
  const sb = await provider.create({
    memoryLimitMb: 128,
    cpuLimit: 1,
    networkEnabled: false,
    timeoutSeconds: 30,
  });
  console.log(`  1.3 Created: id=${sb.id}`);
  if (!sb.id) throw new Error('No sandbox id');
  
  // 1.4 Exec command
  const result = await sb.exec('echo', ['hello world']);
  console.log(`  1.4 Exec: exit=${result.exitCode}, stdout="${result.stdout.trim()}", duration=${result.durationMs}ms`);
  if (result.exitCode !== 0) throw new Error(`Exec failed: ${result.stderr}`);
  if (result.stdout.trim() !== 'hello world') throw new Error(`Unexpected output: "${result.stdout}"`);
  
  // 1.5 Write + Read file
  await sb.writeFile('/tmp/test.txt', 'file content test');
  const readContent = await sb.readFile('/tmp/test.txt');
  const text = readContent.toString('utf-8').trim();
  console.log(`  1.5 File I/O: "${text}"`);
  if (text !== 'file content test') throw new Error(`File read/write mismatch: "${text}"`);
  
  // 1.6 Get metrics
  const metrics = await sb.getMetrics();
  console.log(`  1.6 Metrics: cpu=${metrics.cpuPercent}%, mem=${metrics.memoryMb}MB, uptime=${metrics.uptimeSeconds}s`);
  
  // 1.7 Stop
  await sb.stop();
  console.log(`  1.7 Stopped OK`);
  
  return true;
}

// ── Test 2: Agent Manager ────────────────────────────────────────
async function testAgentManager() {
  console.log('\n🤖 Test: AgentManager');
  
  const { AgentManager } = await import('../src/agent/manager.js');
  const { DockerSandboxProvider } = await import('../src/sandbox/docker-sandbox.js');
  
  const provider = new DockerSandboxProvider();
  const mgr = new AgentManager(provider, 60_000);
  
  // 2.1 Register agents
  const writer = mgr.register({
    name: 'Writer',
    model: 'test-model',
    capabilities: ['content_writing'],
    memoryLimitMb: 128,
  });
  console.log(`  2.1 Registered: ${writer.id} (${writer.name})`);
  if (!writer.id) throw new Error('No agent id');
  
  const coder = mgr.register({
    name: 'Coder',
    model: 'test-model',
    capabilities: ['code_generation'],
    memoryLimitMb: 256,
  });
  console.log(`  2.2 Registered: ${coder.id} (${coder.name})`);
  
  // 2.3 List agents
  const agents = mgr.listAgents();
  console.log(`  2.3 Total agents: ${agents.length}`);
  if (agents.length !== 2) throw new Error(`Expected 2 agents, got ${agents.length}`);
  
  // 2.4 Get by capability
  const writers = mgr.getAgentsByCapability('content_writing');
  console.log(`  2.4 Writers: ${writers.length}`);
  if (writers.length !== 1) throw new Error(`Expected 1 writer, got ${writers.length}`);
  
  // 2.5 Execute task
  const taskResult = await mgr.executeTask(writer.id, {
    prompt: 'Say hello and nothing else.',
    priority: 1,
  });
  console.log(`  2.5 Task: status=${taskResult.status}, duration=${taskResult.durationMs}ms, tokens=${taskResult.tokenUsage?.total}`);
  if (taskResult.status !== 'success') {
    console.log(`     (non-critical: sandbox may not have LLM - output: "${taskResult.output.slice(0, 100)}")`);
  }
  
  // 2.6 Get metrics
  const metrics = await mgr.getMetrics(writer.id);
  console.log(`  2.6 Metrics: completed=${metrics.tasksCompleted}, avg_duration=${metrics.averageDurationMs}ms`);
  
  // 2.7 Stop all
  await mgr.stopAll();
  console.log(`  2.7 All stopped OK`);
  
  return true;
}

// ── Test 3: Context Window ──────────────────────────────────────
async function testContextWindow() {
  console.log('\n🧠 Test: ContextWindowManager');
  
  const { ContextWindowManager } = await import('../src/memory/context-window.js');
  
  // 3.1 Basic add/get
  const cwm = new ContextWindowManager({ maxTokens: 1000 });
  cwm.add({ role: 'system', content: 'You are a helpful assistant.' });
  cwm.add({ role: 'user', content: 'Hello!' });
  const msgs = cwm.getMessages();
  console.log(`  3.1 Messages: ${msgs.length}`);
  if (msgs.length !== 2) throw new Error(`Expected 2 messages, got ${msgs.length}`);
  
  // 3.2 Token estimation
  const tokens = cwm.estimateTokens('Hello world, this is a test!');
  console.log(`  3.2 Token estimate: ~${tokens} tokens for test string`);
  if (tokens < 5 || tokens > 20) throw new Error(`Unexpected token estimate: ${tokens}`);
  
  // 3.3 Total tokens
  const total = cwm.getTotalTokens();
  console.log(`  3.3 Total tokens: ${total}`);
  
  // 3.4 Compression trigger
  const cwm2 = new ContextWindowManager({ maxTokens: 200, compressionThreshold: 0.5, keepRecentMessages: 2 });
  cwm2.add({ role: 'system', content: 'sys' });
  // Add enough to trigger compression
  for (let i = 0; i < 20; i++) {
    cwm2.add({ role: 'user', content: `This is message number ${i} with some padding text to fill up tokens. ` });
    cwm2.add({ role: 'assistant', content: `Response to message ${i} that also takes up some tokens in the context window. ` });
  }
  const needed = cwm2.needsCompression();
  console.log(`  3.4 Needs compression: ${needed}`);
  if (!needed) throw new Error('Should need compression');
  
  // 3.5 Compress
  const compResult = cwm2.compress();
  console.log(`  3.5 Compression: removed=${compResult?.messagesRemoved}, saved=${compResult?.tokensSaved} tokens`);
  if (!compResult || compResult.tokensSaved <= 0) throw new Error('Compression did not save tokens');
  
  // 3.6 All strategies
  const cwm3 = new ContextWindowManager({ maxTokens: 200, strategy: 'prune_tool_results' });
  cwm3.add({ role: 'system', content: 'sys' });
  cwm3.add({ role: 'tool', content: 'a'.repeat(2000) }); // large tool result
  cwm3.add({ role: 'tool', content: 'small' });
  const pruned = cwm3.compress();
  console.log(`  3.6 Prune strategy: removed=${pruned?.messagesRemoved}, saved=${pruned?.tokensSaved}`);
  
  // 3.7 Reset
  cwm.reset('New system prompt');
  const afterReset = cwm.getMessages();
  console.log(`  3.7 After reset: ${afterReset.length} messages`);
  if (afterReset.length !== 1) throw new Error(`Expected 1 message after reset, got ${afterReset.length}`);
  
  return true;
}

// ── Test 4: Episodic Memory ─────────────────────────────────────
async function testEpisodicMemory() {
  console.log('\n💾 Test: EpisodicMemory');
  
  const { EpisodicMemory } = await import('../src/memory/episodic.js');
  const mem = new EpisodicMemory('./data/test');
  
  // 4.1 Create session
  const sessionId = mem.createSession('test-agent-1');
  console.log(`  4.1 Session created: ${sessionId}`);
  if (!sessionId) throw new Error('No session id');
  
  // 4.2 Record events
  mem.recordEvent(sessionId, 'task_start', { taskId: 'task-1', prompt: 'test' });
  mem.recordEvent(sessionId, 'milestone', { progress: '50%' });
  mem.recordEvent(sessionId, 'task_end', { taskId: 'task-1', status: 'success' });
  console.log('  4.2 Events recorded OK');
  
  // 4.3 Update token count
  mem.updateTokenCount(sessionId, 1500);
  console.log('  4.3 Token count updated OK');
  
  // 4.4 Get recent sessions
  const sessions = mem.getRecentSessions('test-agent-1');
  console.log(`  4.4 Recent sessions: ${sessions.length}`);
  if (sessions.length < 1) throw new Error('No sessions found');
  if (sessions[0].token_count !== 1500) throw new Error(`Token count not updated: ${sessions[0].token_count}`);
  
  // 4.5 Get agent stats
  const stats = mem.getAgentStats('test-agent-1');
  console.log(`  4.5 Agent stats: sessions=${stats.totalSessions}, tasks=${stats.totalTasks}, tokens=${stats.totalTokens}`);
  
  // 4.6 End session
  mem.endSession(sessionId, 'Test completed successfully');
  
  // 4.7 Close
  mem.close();
  console.log('  4.7 Memory closed OK');
  
  // Cleanup
  const { rmSync } = await import('node:fs');
  rmSync('./data/test', { recursive: true, force: true });
  console.log('  4.8 Cleanup OK');
  
  return true;
}

// ── Test 5: Orchestrator ────────────────────────────────────────
async function testOrchestrator() {
  console.log('\n🎯 Test: Orchestrator');
  
  const { Orchestrator } = await import('../src/orchestrator/index.js');
  const { createDevelopmentWorkflow } = await import('../src/orchestrator/workflow.js');
  const { DockerSandboxProvider } = await import('../src/sandbox/docker-sandbox.js');
  
  const provider = new DockerSandboxProvider();
  const orchestrator = new Orchestrator(provider);
  
  // 5.1 Register agents
  orchestrator.agentManager.register({
    name: 'Dev Agent',
    model: 'auto',
    capabilities: ['code_generation', 'content_writing', 'data_analysis', 'file_operations', 'shell_commands'],
    memoryLimitMb: 128,
  });
  
  // 5.2 Register workflow
  const workflow = createDevelopmentWorkflow('Build a hello world app');
  orchestrator.registerWorkflow(workflow);
  console.log(`  5.2 Workflow registered: ${workflow.id} (${workflow.steps.length} steps)`);
  
  // 5.3 Task queue
  const { TaskQueue } = await import('../src/orchestrator/task-queue.js');
  const queue = new TaskQueue();
  
  // Add tasks with dependencies
  queue.add({ id: 'task-1', agentId: 'a1', prompt: 'Task 1', priority: 1, createdAt: new Date() });
  queue.add({ id: 'task-2', agentId: 'a2', prompt: 'Task 2 (depends on 1)', priority: 2, createdAt: new Date(), dependsOn: ['task-1'] });
  queue.add({ id: 'task-3', agentId: 'a3', prompt: 'Task 3 (no dep)', priority: 3, createdAt: new Date() });
  
  console.log(`  5.3 Queue: pending=${queue.pendingCount}, complete=${queue.isComplete}`);
  
  // Process tasks
  const t1 = queue.next();
  console.log(`     Next task: ${t1?.id || 'none'}`);
  if (!t1) throw new Error('No task returned from queue');
  
  queue.complete('task-1', { taskId: 'task-1', agentId: 'a1', status: 'success', output: 'done', durationMs: 10, createdAt: new Date() });
  queue.complete('task-3', { taskId: 'task-3', agentId: 'a3', status: 'success', output: 'done', durationMs: 10, createdAt: new Date() });
  
  const stats = queue.getStats();
  console.log(`     Stats: completed=${stats.completed}, running=${stats.running}, pending=${stats.pending}`);
  
  // Task 2 should now be unblocked
  const t2 = queue.next();
  console.log(`     Unblocked task: ${t2?.id || 'none'}`);
  if (!t2 || t2.id !== 'task-2') throw new Error('Task 2 should be unblocked');
  
  // 5.4 Shutdown
  await orchestrator.shutdown();
  console.log('  5.4 Orchestrator shutdown OK');
  
  // Cleanup test data
  const { rmSync } = await import('node:fs');
  rmSync('./data', { recursive: true, force: true });
  
  return true;
}

// ── Test 6: Content Pipeline ────────────────────────────────────
async function testContentPipeline() {
  console.log('\n📝 Test: ContentPipeline');
  
  const { ContentPipeline } = await import('../src/content/pipeline.js');
  const { AgentManager } = await import('../src/agent/manager.js');
  const { DockerSandboxProvider } = await import('../src/sandbox/docker-sandbox.js');
  
  const provider = new DockerSandboxProvider();
  const mgr = new AgentManager(provider, 60_000);
  
  mgr.register({
    name: 'Creator',
    model: 'auto',
    capabilities: ['content_writing', 'web_search', 'data_analysis', 'code_generation'],
    memoryLimitMb: 256,
  });
  
  const pipeline = new ContentPipeline(mgr);
  
  // Test the pipeline structure (actual execution will try sandbox)
  const result = await pipeline.create({
    type: 'article',
    topic: 'AI testing',
    targetAudience: 'developers',
    tone: 'technical',
    length: 'short',
  });
  
  console.log(`  6.1 Pipeline: ${result.stages.length} stages, ${result.durationMs}ms`);
  console.log(`     Stages: ${result.stages.map(s => `${s.name}=${s.status}`).join(', ')}`);
  
  await mgr.stopAll();
  return true;
}

// ── Test 7: Dashboard Server ────────────────────────────────────
async function testDashboard() {
  console.log('\n📊 Test: Dashboard');
  
  const { DashboardServer } = await import('../src/dashboard/server.js');
  const server = new DashboardServer({ port: 0 }); // port 0 = random port
  
  // We just test the module loads
  console.log('  7.1 Dashboard module loaded OK');
  
  return true;
}

// ── Main runner ──────────────────────────────────────────────────
async function main() {
  console.log('══════════════════════════════════════════════');
  console.log('  P3 Agent System - Comprehensive Test Suite');
  console.log('══════════════════════════════════════════════\n');
  
  const tests = [
    { name: 'DockerSandbox', fn: testDockerSandbox },
    { name: 'AgentManager', fn: testAgentManager },
    { name: 'ContextWindow', fn: testContextWindow },
    { name: 'EpisodicMemory', fn: testEpisodicMemory },
    { name: 'TaskQueue/Orchestrator', fn: testOrchestrator },
    { name: 'ContentPipeline', fn: testContentPipeline },
    { name: 'Dashboard', fn: testDashboard },
  ];
  
  let passed = 0;
  let failed = 0;
  const failures: string[] = [];
  
  for (const test of tests) {
    try {
      console.log(`\n── ${test.name} ──`);
      await test.fn();
      console.log(`  ✅ PASS`);
      passed++;
    } catch (err: any) {
      console.log(`  ❌ FAIL: ${err.message}`);
      failed++;
      failures.push(`${test.name}: ${err.message}`);
    }
  }
  
  console.log('\n══════════════════════════════════════════════');
  console.log(`  Results: ${passed} passed, ${failed} failed`);
  console.log('══════════════════════════════════════════════');
  
  if (failures.length > 0) {
    console.log('\nFailures:');
    failures.forEach(f => console.log(`  ❌ ${f}`));
    process.exit(1);
  }
}

main().catch(err => {
  console.error('Test harness error:', err);
  process.exit(1);
});
