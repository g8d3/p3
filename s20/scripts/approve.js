#!/usr/bin/env node
/**
 * CLI tool to manage approval queue
 * Usage:
 *   node approve.js              - List all pending approvals
 *   node approve.js <id>         - Show details for specific approval
 *   node approve.js <id> approve [note]  - Approve an item
 *   node approve.js <id> reject [note]   - Reject an item
 */

import 'dotenv/config';
import { stateManager } from '../src/infrastructure/state.js';

function printUsage() {
  console.log(`
Usage:
  node approve.js                        List all pending approvals
  node approve.js <id>                   Show details for specific approval
  node approve.js <id> approve [note]    Approve an item
  node approve.js <id> reject [note]     Reject an item
`);
}

async function listApprovals() {
  const approvals = stateManager.getPendingApprovals();
  
  if (approvals.length === 0) {
    console.log('\nNo pending approvals.\n');
    return;
  }

  console.log(`\nPending Approvals (${approvals.length}):\n`);
  console.log('ID    | Type                    | Created At');
  console.log('-'.repeat(60));

  for (const approval of approvals) {
    const id = String(approval.id).padEnd(5);
    const type = approval.action_type.substring(0, 23).padEnd(23);
    const created = new Date(approval.created_at).toISOString();
    console.log(`${id} | ${type} | ${created}`);
  }

  console.log('\nUse "node approve.js <id>" to see details.');
  console.log('Use "node approve.js <id> approve/reject [note]" to resolve.\n');
}

async function showApprovalDetails(id) {
  const approval = stateManager.queryOne(
    'SELECT * FROM approval_queue WHERE id = ?',
    [id]
  );

  if (!approval) {
    console.error(`\nError: Approval with ID ${id} not found.\n`);
    process.exit(1);
  }

  console.log('\n=== Approval Details ===\n');
  console.log(`ID:         ${approval.id}`);
  console.log(`Status:     ${approval.status}`);
  console.log(`Type:       ${approval.action_type}`);
  console.log(`Created:    ${new Date(approval.created_at).toISOString()}`);
  
  if (approval.reviewed_at) {
    console.log(`Reviewed:   ${new Date(approval.reviewed_at).toISOString()}`);
    console.log(`Note:       ${approval.reviewer_note || 'N/A'}`);
  }

  console.log('\nAction Data:');
  try {
    const data = JSON.parse(approval.action_data);
    console.log(JSON.stringify(data, null, 2));
  } catch {
    console.log(approval.action_data);
  }
  console.log('');

  if (approval.status === 'pending') {
    console.log('To approve: node approve.js ' + id + ' approve [note]');
    console.log('To reject:  node approve.js ' + id + ' reject [note]');
  }
  console.log('');
}

async function resolveApproval(id, approved, note = null) {
  const approval = stateManager.queryOne(
    'SELECT * FROM approval_queue WHERE id = ?',
    [id]
  );

  if (!approval) {
    console.error(`\nError: Approval with ID ${id} not found.\n`);
    process.exit(1);
  }

  if (approval.status !== 'pending') {
    console.error(`\nError: Approval ${id} is already ${approval.status}.\n`);
    process.exit(1);
  }

  stateManager.resolveApproval(id, approved, note);

  const action = approved ? 'approved' : 'rejected';
  console.log(`\nApproval ${id} has been ${action}.`);
  
  if (note) {
    console.log(`Note: ${note}`);
  }
  console.log('');
}

async function main() {
  const args = process.argv.slice(2);

  try {
    stateManager.init();

    if (args.length === 0) {
      // List all pending approvals
      await listApprovals();
    } else if (args[0] === '--help' || args[0] === '-h') {
      printUsage();
    } else {
      const id = parseInt(args[0], 10);

      if (isNaN(id)) {
        console.error('\nError: Invalid approval ID. Must be a number.\n');
        printUsage();
        process.exit(1);
      }

      if (args.length === 1) {
        // Show details
        await showApprovalDetails(id);
      } else {
        const action = args[1].toLowerCase();
        
        if (action === 'approve' || action === 'accept' || action === 'yes') {
          const note = args.slice(2).join(' ') || null;
          await resolveApproval(id, true, note);
        } else if (action === 'reject' || action === 'deny' || action === 'no') {
          const note = args.slice(2).join(' ') || null;
          await resolveApproval(id, false, note);
        } else {
          console.error(`\nError: Unknown action "${action}". Use "approve" or "reject".\n`);
          process.exit(1);
        }
      }
    }

    process.exit(0);
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  } finally {
    stateManager.close();
  }
}

main();
