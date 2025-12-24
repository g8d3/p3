
console.log("Loading imports...");

// Setup file logging
const logFile = Bun.file("server.log");
const logger = {
  log: (message: string, level: 'INFO' | 'ERROR' | 'WARN' = 'INFO') => {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] [${level}] ${message}\n`;
    console.log(logMessage.trim());
    // Append to log file
    Bun.write(logFile, logMessage, { createPath: true });
  },
  error: (message: string, error?: any) => {
    logger.log(`ERROR: ${message}${error ? ` - ${error.stack || error.message || error}` : ''}`, 'ERROR');
  },
  warn: (message: string) => {
    logger.log(`WARN: ${message}`, 'WARN');
  }
};

logger.log("Starting AI Scraper Server...");

import { serve } from "bun";
logger.log("Bun imported");

import PocketBase from 'pocketbase';
logger.log("PocketBase imported");

import pb from "./api/pocketbase";
logger.log("PB client imported");

import { discoverExtractionTargets } from "./ai/discovery";
logger.log("Discovery imported");

import { generateScrapingCode } from "./ai/codegen";
logger.log("Codegen imported");

import puppeteer from 'puppeteer-core';
logger.log("Puppeteer imported");

import cron from 'node-cron';
logger.log("Cron imported");

// Initialize collections if they don't exist (non-blocking)
async function initializeCollections() {
  try {
    // Try to get one of our collections to see if they exist
    await pb.collection('ai_models').getFirstListItem('id != ""');
    logger.log('Collections already exist and are accessible');
    return; // Skip initialization
  } catch (e) {
    // Collections don't exist or aren't accessible, create them
    logger.log('Initializing collections...');

    // For fresh PocketBase, create collections directly via HTTP
    // First, try to create admin if needed
    let adminToken = null;

    try {
      // Try to create admin
      const adminResponse = await fetch('http://127.0.0.1:8090/api/admins', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'admin@example.com',
          password: 'admin123123',
          passwordConfirm: 'admin123123'
        })
      });

      if (adminResponse.ok) {
        console.log('Admin created successfully');
      }

      // Now authenticate as admin
      const authResponse = await fetch('http://127.0.0.1:8090/api/admins/auth-with-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          identity: 'admin@example.com',
          password: 'admin123123'
        })
      });

      if (authResponse.ok) {
        const authData = await authResponse.json();
        adminToken = authData.token;
        console.log('Admin authenticated successfully');
      }
    } catch (authError) {
      console.log('Admin setup failed, trying direct collection creation:', authError.message);
    }

    const collections = [
      {
        name: 'ai_models',
        type: 'base',
        schema: [
          { name: 'name', type: 'text', required: true },
          { name: 'api_key', type: 'text', required: true },
          { name: 'api_url', type: 'text', required: true },
          { name: 'model_id', type: 'text', required: true },
          { name: 'owner', type: 'relation', required: true, options: { collectionId: '_pb_users_auth_', cascadeDelete: true, maxSelect: 1 } }
        ],
        listRule: '@request.auth.id = owner.id',
        viewRule: '@request.auth.id = owner.id',
        createRule: '@request.auth.id != ""',
        updateRule: '@request.auth.id = owner.id',
        deleteRule: '@request.auth.id = owner.id',
      },
      {
        name: 'browsers',
        type: 'base',
        schema: [
          { name: 'name', type: 'text', required: true },
          { name: 'cdp_url', type: 'text', required: true },
          { name: 'owner', type: 'relation', required: true, options: { collectionId: '_pb_users_auth_', cascadeDelete: true, maxSelect: 1 } }
        ],
        listRule: '@request.auth.id = owner.id',
        viewRule: '@request.auth.id = owner.id',
        createRule: '@request.auth.id != ""',
        updateRule: '@request.auth.id = owner.id',
        deleteRule: '@request.auth.id = owner.id',
      },
      {
        name: 'data_sinks',
        type: 'base',
        schema: [
          { name: 'name', type: 'text', required: true },
          { name: 'type', type: 'select', required: true, options: { values: ['webhook', 's3', 'pocketbase', 'custom_api'] } },
          { name: 'config', type: 'json', required: false },
          { name: 'owner', type: 'relation', required: true, options: { collectionId: '_pb_users_auth_', cascadeDelete: true, maxSelect: 1 } }
        ],
        listRule: '@request.auth.id = owner.id',
        viewRule: '@request.auth.id = owner.id',
        createRule: '@request.auth.id != ""',
        updateRule: '@request.auth.id = owner.id',
        deleteRule: '@request.auth.id = owner.id',
      },
      {
        name: 'scrapers',
        type: 'base',
        schema: [
          { name: 'name', type: 'text', required: true },
          { name: 'url', type: 'url', required: true },
          { name: 'ai_model', type: 'relation', required: false, options: { collectionId: 'ai_models', maxSelect: 1 } },
          { name: 'browser', type: 'relation', required: false, options: { collectionId: 'browsers', maxSelect: 1 } },
          { name: 'code', type: 'text', required: false },
          { name: 'discovery_options', type: 'json', required: false },
          { name: 'selected_option', type: 'text', required: false },
          { name: 'schedule', type: 'text', required: false },
          { name: 'data_sink', type: 'relation', required: false, options: { collectionId: 'data_sinks', maxSelect: 1 } },
          { name: 'owner', type: 'relation', required: true, options: { collectionId: '_pb_users_auth_', cascadeDelete: true, maxSelect: 1 } }
        ],
        listRule: '@request.auth.id != ""',
        viewRule: '@request.auth.id = owner.id',
        createRule: '@request.auth.id != ""',
        updateRule: '@request.auth.id = owner.id',
        deleteRule: '@request.auth.id = owner.id',
      },
      {
        name: 'extraction_runs',
        type: 'base',
        schema: [
          { name: 'scraper', type: 'relation', required: true, options: { collectionId: 'scrapers', cascadeDelete: true, maxSelect: 1 } },
          { name: 'status', type: 'select', required: true, options: { values: ['pending', 'running', 'completed', 'failed'] } },
          { name: 'started_at', type: 'date', required: false },
          { name: 'finished_at', type: 'date', required: false },
          { name: 'steps', type: 'json', required: false },
          { name: 'output_data', type: 'json', required: false },
          { name: 'errors', type: 'json', required: false }
        ],
        listRule: '@request.auth.id = scraper.owner.id',
        viewRule: '@request.auth.id = scraper.owner.id',
        createRule: '@request.auth.id != ""',
        updateRule: '@request.auth.id = scraper.owner.id',
        deleteRule: '@request.auth.id = scraper.owner.id',
      },
      {
        name: 'tests',
        type: 'base',
        schema: [
          { name: 'scraper', type: 'relation', required: true, options: { collectionId: 'scrapers', cascadeDelete: true, maxSelect: 1 } },
          { name: 'name', type: 'text', required: true },
          { name: 'code', type: 'text', required: true },
          { name: 'owner', type: 'relation', required: true, options: { collectionId: '_pb_users_auth_', cascadeDelete: true, maxSelect: 1 } }
        ],
        listRule: '@request.auth.id = owner.id',
        viewRule: '@request.auth.id = owner.id',
        createRule: '@request.auth.id != ""',
        updateRule: '@request.auth.id = owner.id',
        deleteRule: '@request.auth.id = owner.id',
      },
      {
        name: 'test_runs',
        type: 'base',
        schema: [
          { name: 'test', type: 'relation', required: true, options: { collectionId: 'tests', cascadeDelete: true, maxSelect: 1 } },
          { name: 'status', type: 'select', required: true, options: { values: ['pass', 'fail'] } },
          { name: 'logs', type: 'json', required: false },
          { name: 'run_at', type: 'date', required: false }
        ],
        listRule: '@request.auth.id = test.owner.id',
        viewRule: '@request.auth.id = test.owner.id',
        createRule: '@request.auth.id != ""',
        updateRule: '@request.auth.id = test.owner.id',
        deleteRule: '@request.auth.id = test.owner.id',
      }
    ];

    // Create collections via HTTP API (sort by dependency order)
    const sortedCollections = collections.sort((a, b) => {
      // Base collections first
      const baseCollections = ['ai_models', 'browsers', 'data_sinks', 'scrapers'];
      const relationCollections = ['extraction_runs', 'tests', 'test_runs'];

      if (baseCollections.includes(a.name) && relationCollections.includes(b.name)) return -1;
      if (relationCollections.includes(a.name) && baseCollections.includes(b.name)) return 1;
      return 0;
    });

    for (const collection of sortedCollections) {
      try {
        const headers = { 'Content-Type': 'application/json' };
        if (adminToken) {
          headers['Authorization'] = `Bearer ${adminToken}`;
        }

        // First try to delete if exists
        try {
          await fetch('http://127.0.0.1:8090/api/collections/' + collection.name, {
            method: 'DELETE',
            headers
          });
          logger.log(`Deleted existing collection: ${collection.name}`);
        } catch (e) {
          // Collection doesn't exist, that's fine
        }

        // Now create the collection
        const response = await fetch('http://127.0.0.1:8090/api/collections', {
          method: 'POST',
          headers,
          body: JSON.stringify(collection)
        });

        if (response.ok) {
          logger.log(`Created collection: ${collection.name}`);
        } else {
          logger.error(`Failed to create collection ${collection.name}: ${response.status} - ${response.statusText}`);
          const errorText = await response.text();
          logger.error(`Error details: ${errorText}`);
        }
      } catch (e) {
        console.log(`Error creating collection ${collection.name}:`, e.message);
      }
    }

    logger.log('Collections initialization completed');
  }
}

// Scheduler
const scheduledJobs: Record<string, any> = {};

// Update scheduler on startup
async function updateScheduler() {
  try {
    const scrapers = await pb.collection('scrapers').getFullList({
      filter: 'schedule != ""'
    });

    // Clear existing jobs
    for (const job of Object.values(scheduledJobs)) {
      job.destroy();
    }

    // Register new jobs
    for (const scraper of scrapers) {
      if (cron.validate(scraper.schedule)) {
        scheduledJobs[scraper.id] = cron.schedule(scraper.schedule, () => {
          console.log(`Scheduled run for scraper ${scraper.id}`);
          executeScraper(scraper.id).catch(console.error);
        });
      }
    }
  } catch (e) {
    // Collections might not exist yet, skip
  }
}

// Initialize collections asynchronously (don't block server startup)
// Temporarily disabled - collections created manually
// setTimeout(() => {
//   initializeCollections().then(() => {
//     console.log('Database initialized');
//     return updateScheduler();
//   }).catch(err => {
//     console.error('Failed to initialize database:', err.message);
//     console.log('Server will continue without database initialization');
//   });
// }, 100);


async function sendToSink(sink: any, data: any, scraperId: string) {
  switch (sink.type) {
    case 'webhook':
      await fetch(sink.config.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      break;
    case 's3':
      // Implement S3 upload
      // For now, just log
      console.log('S3 upload would happen here');
      break;
    case 'pocketbase':
      // Insert into another PB collection
      const pbClient = new PocketBase(sink.config.url);
      await pbClient.collection(sink.config.collection).create({ data, scraper: scraperId });
      break;
    case 'custom_api':
      await fetch(sink.config.url, {
        method: sink.config.method || 'POST',
        headers: sink.config.headers || { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      break;
  }
}

async function executeScraper(scraperId: string) {
    const scraper = await pb.collection('scrapers').getOne(scraperId, { expand: 'browser,data_sink' });

    if (!scraper.expand?.browser) {
      throw new Error('Browser not configured');
    }

    const run = await pb.collection('extraction_runs').create({
      scraper: scraperId,
      status: 'running',
      started_at: new Date().toISOString(),
      steps: []
    });

    const logStep = async (message: string, details?: any) => {
      const currentRun = await pb.collection('extraction_runs').getOne(run.id);
      const steps = currentRun.steps || [];
      steps.push({ timestamp: new Date().toISOString(), message, details });
      await pb.collection('extraction_runs').update(run.id, { steps });
    };

    try {
        await logStep("Connecting to browser", { cdp_url: scraper.expand.browser.cdp_url });
        const browser = await puppeteer.connect({ browserWSEndpoint: scraper.expand.browser.cdp_url });
        const page = await browser.newPage();

        await logStep("Navigating to URL", { url: scraper.url });
        await page.goto(scraper.url, { waitUntil: 'networkidle2' });

        await logStep("Executing extraction code");
        const extractionFn = new Function('page', `return (${scraper.code.split('async function testExtract')[0]})`);
        const data = await (extractionFn(page))(page);

        await logStep("Extraction complete", { dataCount: Array.isArray(data) ? data.length : 1 });

        await pb.collection('extraction_runs').update(run.id, {
          status: 'completed',
          finished_at: new Date().toISOString(),
          output_data: data
        });

        if (scraper.expand?.data_sink) {
          await logStep("Sending to data sink", { type: scraper.expand.data_sink.type });
          try {
            await sendToSink(scraper.expand.data_sink, data, scraperId);
            await logStep("Data sent to sink successfully");
          } catch (e: any) {
            await logStep("Failed to send to sink", { error: e.message });
            // Don't fail the whole run for sink errors
          }
        }

        await page.close();
        await browser.disconnect();
        return data;
      } catch (e: any) {
        await logStep("Error during run", { error: e.message });
        await pb.collection('extraction_runs').update(run.id, {
          status: 'failed',
          finished_at: new Date().toISOString(),
          errors: [{ message: e.message }]
        });
        throw e;
      }
}

logger.log('Starting server...');

try {
  const server = serve({
    port: 3000,
    async fetch(req) {
    console.log(`Request: ${req.method} ${req.url}`);
    const url = new URL(req.url);
    const path = url.pathname;

    // Basic API routing
    if (path === "/api/discover" && req.method === "POST") {
      try {
        logger.log(`API: /api/discover called`);
        const { scraperId } = await req.json();
        const scraper = await pb.collection('scrapers').getOne(scraperId, { expand: 'ai_model,browser' });

        if (!scraper.expand?.ai_model || !scraper.expand?.browser) {
          logger.warn(`API: Missing AI model or Browser config for scraper ${scraperId}`);
          return new Response(JSON.stringify({ error: "Missing AI model or Browser config" }), { status: 400 });
        }

        logger.log(`API: Starting AI discovery for URL: ${scraper.url}`);
        const options = await discoverExtractionTargets(
          scraper.url,
          scraper.expand.browser.cdp_url,
          {
            apiKey: scraper.expand.ai_model.api_key,
            apiUrl: scraper.expand.ai_model.api_url,
            modelId: scraper.expand.ai_model.model_id
          }
        );

        await pb.collection('scrapers').update(scraperId, { discovery_options: { options } });
        logger.log(`API: Discovery completed for scraper ${scraperId}`);
        return new Response(JSON.stringify({ options }));
      } catch (e: any) {
        logger.error(`API: /api/discover error for scraper ${req.json?.()?.scraperId || 'unknown'}`, e);
        return new Response(JSON.stringify({ error: e.message }), { status: 500 });
      }
    }

    if (path === "/api/generate-code" && req.method === "POST") {
      try {
        logger.log(`API: /api/generate-code called`);
        const { scraperId, selectedOption } = await req.json();
        const scraper = await pb.collection('scrapers').getOne(scraperId, { expand: 'ai_model' });

        const option = scraper.discovery_options?.options?.find((o: any) => o.title === selectedOption);
        if (!option) {
          logger.warn(`API: Selected option '${selectedOption}' not found for scraper ${scraperId}`);
          return new Response(JSON.stringify({ error: "Selected option not found" }), { status: 400 });
        }

        logger.log(`API: Generating code for scraper ${scraperId}, option: ${selectedOption}`);
        const code = await generateScrapingCode(
          scraper.url,
          option,
          {
            apiKey: scraper.expand.ai_model.api_key,
            apiUrl: scraper.expand.ai_model.api_url,
            modelId: scraper.expand.ai_model.model_id
          }
        );

        await pb.collection('scrapers').update(scraperId, { code, selected_option: selectedOption });
        logger.log(`API: Code generation completed for scraper ${scraperId}`);
        return new Response(JSON.stringify({ code }));
      } catch (e: any) {
        logger.error(`API: /api/generate-code error`, e);
        return new Response(JSON.stringify({ error: e.message }), { status: 500 });
      }
    }

    if (path === "/api/run" && req.method === "POST") {
        try {
          logger.log(`API: /api/run called`);
          const { scraperId } = await req.json();

          logger.log(`API: Starting scraper execution for ${scraperId}`);
          // Start execution in background
          executeScraper(scraperId).catch(e => {
            logger.error(`API: Scraper execution failed for ${scraperId}`, e);
          });

          return new Response(JSON.stringify({ message: "Run started" }));
        } catch (e: any) {
          logger.error(`API: /api/run error`, e);
          return new Response(JSON.stringify({ error: e.message }), { status: 500 });
        }
    }

    if (path === "/api/run-test" && req.method === "POST") {
        try {
          const { testId } = await req.json();
          const test = await pb.collection('tests').getOne(testId, { expand: 'scraper,scraper.browser' });

          if (!test.expand?.scraper || !test.expand.scraper.expand?.browser) {
            return new Response(JSON.stringify({ error: "Test configuration incomplete" }), { status: 400 });
          }

          const scraper = test.expand.scraper;

          const run = await pb.collection('test_runs').create({
            test: testId,
            status: 'pending',
            logs: [],
            run_at: new Date().toISOString()
          });

          (async () => {
            const logs: any[] = [];
            const addLog = async (msg: string, details?: any) => {
              logs.push({ timestamp: new Date().toISOString(), msg, details });
              await pb.collection('test_runs').update(run.id, { logs });
            };

            try {
              await addLog("Connecting to browser");
              const browser = await puppeteer.connect({ browserWSEndpoint: scraper.expand.browser.cdp_url });
              const page = await browser.newPage();

              await addLog("Navigating to URL", { url: scraper.url });
              await page.goto(scraper.url, { waitUntil: 'networkidle2' });

              await addLog("Executing extraction");
              const extractionFn = new Function('page', `return (${scraper.code.split('async function testExtract')[0]})`);
              const data = await (extractionFn(page))(page);

              await addLog("Running test code");
              // The test code is expected to have a testExtract(data) function
              const testFn = new Function('data', `return (${scraper.code.split('async function testExtract')[1] || test.code})`);
              const result = await (testFn(data))(data);

              await addLog("Test finished", { result });

              await pb.collection('test_runs').update(run.id, {
                status: result.success ? 'pass' : 'fail',
                logs: logs
              });

              await page.close();
              await browser.disconnect();
            } catch (e: any) {
              await addLog("Test error", { error: e.message });
              await pb.collection('test_runs').update(run.id, {
                status: 'fail',
              });
            }
          })();

          return new Response(JSON.stringify({ runId: run.id }));
        } catch (e: any) {
          return new Response(JSON.stringify({ error: e.message }), { status: 500 });
        }
    }

    // Serve static files (simplified for now)

    if (path === "/" || path === "/index.html") {
      try {
        const html = await Bun.file("src/ui/index.html").text();
        return new Response(html, {
          headers: { 'Content-Type': 'text/html' }
        });
      } catch (e) {
        console.error('File error:', e);
        return new Response("File not found", { status: 404 });
      }
    }

    return new Response("Not Found", { status: 404 });
  },
});

logger.log(`Server running at http://localhost:${server.port}`);
} catch (error) {
  logger.error('Server startup error', error);
  process.exit(1);
}
