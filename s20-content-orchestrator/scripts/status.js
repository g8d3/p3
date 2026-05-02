#!/usr/bin/env node
/**
 * CLI tool to show agent status
 * Usage: node status.js
 */

import 'dotenv/config';
import { stateManager } from '../src/infrastructure/state.js';

async function main() {
  try {
    stateManager.init();

    console.log('\n=== Agent Status ===\n');

    // Agent running status
    const isRunning = stateManager.get('agent_running');
    const lastHeartbeat = stateManager.get('last_heartbeat');
    console.log('Agent Status:');
    if (isRunning) {
      console.log('  Running: Yes');
      if (lastHeartbeat) {
        const heartbeatTime = new Date(lastHeartbeat);
        const ageMs = Date.now() - heartbeatTime.getTime();
        const ageSec = Math.floor(ageMs / 1000);
        console.log(`  Last Heartbeat: ${heartbeatTime.toISOString()} (${ageSec}s ago)`);
      }
    } else {
      console.log('  Running: No');
    }

    // Browser connection status
    const browserConnected = stateManager.get('browser_connected');
    const browserLastSeen = stateManager.get('browser_last_seen');
    console.log('\nBrowser Connection:');
    if (browserConnected) {
      console.log('  Connected: Yes');
      if (browserLastSeen) {
        console.log(`  Last Seen: ${new Date(browserLastSeen).toISOString()}`);
      }
    } else {
      console.log('  Connected: No');
    }

    // Scheduled tasks
    console.log('\nScheduled Tasks:');
    const tasks = stateManager.query(
      'SELECT * FROM scheduled_tasks ORDER BY module, action'
    );
    if (tasks.length === 0) {
      console.log('  No scheduled tasks');
    } else {
      for (const task of tasks) {
        const status = task.enabled ? 'enabled' : 'disabled';
        const lastRun = task.last_run ? new Date(task.last_run).toISOString() : 'never';
        const nextRun = task.next_run ? new Date(task.next_run).toISOString() : 'not scheduled';
        console.log(`  [${task.id}] ${task.module}.${task.action}`);
        console.log(`      Cron: ${task.cron_expr} | Status: ${status}`);
        console.log(`      Last Run: ${lastRun} | Next Run: ${nextRun}`);
      }
    }

    // Recent action log (last 10 entries)
    console.log('\nRecent Actions (last 10):');
    const actions = stateManager.getRecentActions(10);
    if (actions.length === 0) {
      console.log('  No recent actions');
    } else {
      for (const action of actions) {
        const timestamp = new Date(action.timestamp).toISOString();
        const duration = action.duration_ms ? `${action.duration_ms}ms` : 'N/A';
        const error = action.error ? ' [ERROR]' : '';
        console.log(`  [${action.id}] ${timestamp} | ${action.module}.${action.action}${error}`);
        if (action.error) {
          console.log(`      Error: ${action.error.substring(0, 100)}${action.error.length > 100 ? '...' : ''}`);
        }
      }
    }

    // Pending approvals count
    const pendingApprovals = stateManager.getPendingApprovals();
    console.log('\nPending Approvals:');
    console.log(`  Count: ${pendingApprovals.length}`);
    if (pendingApprovals.length > 0) {
      console.log('  Waiting for approval:');
      for (const approval of pendingApprovals.slice(0, 5)) {
        const created = new Date(approval.created_at).toISOString();
        console.log(`    [${approval.id}] ${approval.action_type} (created: ${created})`);
      }
      if (pendingApprovals.length > 5) {
        console.log(`    ... and ${pendingApprovals.length - 5} more`);
      }
    }

    // Database stats
    const stats = stateManager.getStats();
    console.log('\nDatabase Statistics:');
    for (const [table, count] of Object.entries(stats)) {
      console.log(`  ${table}: ${count} rows`);
    }

    console.log('\n');
    process.exit(0);
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  } finally {
    stateManager.close();
  }
}

main();
