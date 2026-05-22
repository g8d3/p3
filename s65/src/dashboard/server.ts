#!/usr/bin/env tsx
/**
 * Dashboard server.
 * 
 * Real-time monitoring dashboard for the multi-agent system.
 * Shows:
 *   - Active agents and their status
 *   - Resource usage (CPU, memory per agent/sandbox)
 *   - Task queue status
 *   - Workflow executions
 *   - Real-time event log via WebSocket
 */

import { createServer } from 'node:http';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { WebSocketServer } from 'ws';
import { fileURLToPath } from 'node:url';
import { telemetry } from '../monitor/telemetry.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = join(__dirname, 'public');

interface DashboardConfig {
  port: number;
  orchestrator?: any;
}

export class DashboardServer {
  private config: DashboardConfig;
  private httpServer: ReturnType<typeof createServer> | null = null;
  private wss: WebSocketServer | null = null;

  constructor(config: DashboardConfig) {
    this.config = config;
  }

  async start(): Promise<void> {
    this.httpServer = createServer((req, res) => {
      this.handleRequest(req, res);
    });

    // WebSocket for real-time updates
    this.wss = new WebSocketServer({ server: this.httpServer });
    
    this.wss.on('connection', (ws) => {
      console.log('[dashboard] Client connected');
      
      // Send initial snapshot
      ws.send(JSON.stringify({
        type: 'connected',
        timestamp: Date.now(),
        summary: telemetry.getSummary(),
      }));
      
      // Subscribe to all events
      const unsub = telemetry.subscribe('*', (event) => {
        if (ws.readyState === ws.OPEN) {
          ws.send(JSON.stringify({ msgType: 'event', originalType: event.type, timestamp: event.timestamp, data: event.data }));
        }
      });
      
      ws.on('close', () => {
        unsub();
        console.log('[dashboard] Client disconnected');
      });
    });

    return new Promise((resolve) => {
      this.httpServer!.listen(this.config.port, () => {
        console.log(`\n📊 Dashboard: http://localhost:${this.config.port}`);
        console.log(`   WebSocket: ws://localhost:${this.config.port}\n`);
        resolve();
      });
    });
  }

  private handleRequest(req: any, res: any): void {
    const url = new URL(req.url, `http://localhost:${this.config.port}`);
    let filePath = url.pathname === '/' ? '/index.html' : url.pathname;
    
    // Try to serve from public directory
    const fullPath = join(PUBLIC_DIR, filePath);
    
    if (existsSync(fullPath)) {
      const ext = filePath.split('.').pop() ?? 'html';
      const mimeTypes: Record<string, string> = {
        html: 'text/html',
        css: 'text/css',
        js: 'application/javascript',
        json: 'application/json',
        svg: 'image/svg+xml',
        png: 'image/png',
      };
      
      res.writeHead(200, { 'Content-Type': mimeTypes[ext] ?? 'application/octet-stream' });
      res.end(readFileSync(fullPath));
    } else {
      res.writeHead(404);
      res.end('Not Found');
    }
  }

  stop(): void {
    this.wss?.close();
    this.httpServer?.close();
  }
}

// Allow running standalone
const port = parseInt(process.env.DASHBOARD_PORT ?? '3030');
const server = new DashboardServer({ port });
server.start().catch(console.error);
