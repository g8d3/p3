/**
 * Main Entry Point for Novaisabuilder Agent
 * Initializes and starts the Orchestrator daemon
 */

import dotenv from 'dotenv';
import { getOrchestrator } from './src/orchestrator/index.js';

// Load environment variables
dotenv.config();

// Get orchestrator instance
const orchestrator = getOrchestrator();

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('UNCAUGHT EXCEPTION:', error);
  console.error(error.stack);
  
  // Attempt graceful shutdown
  orchestrator.stop().then(() => {
    process.exit(1);
  }).catch(() => {
    process.exit(1);
  });
});

// Handle unhandled rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('UNHANDLED REJECTION at:', promise);
  console.error('Reason:', reason);
});

// Main startup
async function main() {
  console.log('========================================');
  console.log('  Novaisabuilder Agent Starting...');
  console.log('========================================');
  console.log(`Time: ${new Date().toISOString()}`);
  console.log(`Node: ${process.version}`);
  console.log(`PID: ${process.pid}`);
  console.log('========================================');

  try {
    // Initialize and start
    await orchestrator.start();

    console.log('');
    console.log('Agent started successfully!');
    console.log('Press Ctrl+C to stop.');
    console.log('');

    // Log periodic status
    const statusInterval = setInterval(() => {
      const status = orchestrator.getStatus();
      console.log(`[STATUS] Running: ${status.running} | Browser: ${status.browserConnected} | Scheduler: ${status.schedulerRunning}`);
    }, 60000); // Every minute

    // Clean up interval on shutdown
    orchestrator.on('stopped', () => {
      clearInterval(statusInterval);
    });

  } catch (error) {
    console.error('Failed to start agent:', error);
    console.error(error.stack);
    process.exit(1);
  }
}

// Run main
main();
