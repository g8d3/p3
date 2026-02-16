#!/usr/bin/env node
/**
 * CLI tool to reset agent state (DANGEROUS)
 * Usage:
 *   node reset.js                     - Show what would be reset (dry run)
 *   node reset.js --confirm           - Reset everything (requires confirmation)
 *   node reset.js --confirm --state   - Reset only agent_state table
 *   node reset.js --confirm --content - Reset only content_items table
 *   node reset.js --confirm --approvals - Reset only approval_queue table
 */

import 'dotenv/config';
import { stateManager } from '../src/infrastructure/state.js';

const OPTIONS = {
  state: {
    flag: '--state',
    table: 'agent_state',
    description: 'Clear agent state (keys, settings, runtime data)',
  },
  content: {
    flag: '--content',
    table: 'content_items',
    description: 'Clear content items (drafts, posted content)',
  },
  approvals: {
    flag: '--approvals',
    table: 'approval_queue',
    description: 'Clear approval queue (pending approvals)',
  },
};

function printUsage() {
  console.log(`
Usage:
  node reset.js                      Show what would be reset (dry run)
  node reset.js --confirm            Reset everything (DANGEROUS)
  node reset.js --confirm --state    Reset only agent_state table
  node reset.js --confirm --content  Reset only content_items table
  node reset.js --confirm --approvals Reset only approval_queue table

Options:
  --confirm    Actually perform the reset (required for any changes)
  --state      Clear agent_state table
  --content    Clear content_items table
  --approvals  Clear approval_queue table
  --all        Clear all tables (same as no specific option)

WARNING: This operation cannot be undone!
`);
}

function getTableCounts() {
  const counts = {};
  for (const [key, option] of Object.entries(OPTIONS)) {
    const row = stateManager.queryOne(`SELECT COUNT(*) as count FROM ${option.table}`);
    counts[key] = row.count;
  }
  return counts;
}

function parseArgs(args) {
  const parsed = {
    confirm: false,
    targets: [],
  };

  for (const arg of args) {
    if (arg === '--confirm') {
      parsed.confirm = true;
    } else if (arg === '--all') {
      parsed.targets = Object.keys(OPTIONS);
    } else if (arg === '--help' || arg === '-h') {
      parsed.showHelp = true;
    } else if (arg.startsWith('--')) {
      const optionKey = Object.keys(OPTIONS).find(k => OPTIONS[k].flag === arg);
      if (optionKey && !parsed.targets.includes(optionKey)) {
        parsed.targets.push(optionKey);
      }
    }
  }

  // If no specific targets, target all
  if (parsed.targets.length === 0) {
    parsed.targets = Object.keys(OPTIONS);
  }

  return parsed;
}

async function main() {
  const args = process.argv.slice(2);
  const parsed = parseArgs(args);

  if (parsed.showHelp) {
    printUsage();
    process.exit(0);
  }

  try {
    stateManager.init();

    const counts = getTableCounts();

    if (!parsed.confirm) {
      // Dry run - show what would be reset
      console.log('\n=== RESET PREVIEW (Dry Run) ===\n');
      console.log('The following would be reset:\n');

      let totalRows = 0;
      for (const target of parsed.targets) {
        const option = OPTIONS[target];
        const count = counts[target];
        totalRows += count;
        console.log(`  ${option.flag.padEnd(15)} ${option.table.padEnd(20)} ${count} rows`);
        console.log(`                  ${option.description}`);
        console.log('');
      }

      console.log(`Total rows to be deleted: ${totalRows}`);
      console.log('\nTo actually perform the reset, add --confirm flag:');
      console.log(`  node reset.js --confirm ${parsed.targets.map(t => OPTIONS[t].flag).join(' ')}\n`);

      if (totalRows === 0) {
        console.log('No data to reset.\n');
      }

      process.exit(0);
    }

    // Actual reset with confirmation
    console.log('\n=== RESETTING AGENT STATE ===\n');
    console.log('WARNING: This action cannot be undone!\n');

    let totalDeleted = 0;

    for (const target of parsed.targets) {
      const option = OPTIONS[target];
      const beforeCount = counts[target];
      
      console.log(`Clearing ${option.table}...`);
      stateManager.query(`DELETE FROM ${option.table}`);
      
      console.log(`  Deleted ${beforeCount} rows from ${option.table}`);
      totalDeleted += beforeCount;
    }

    console.log(`\nTotal rows deleted: ${totalDeleted}`);
    console.log('Reset complete.\n');

    process.exit(0);
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  } finally {
    stateManager.close();
  }
}

main();
