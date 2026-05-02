#!/usr/bin/env node

const { Command } = require('commander');
const inquirer = require('inquirer');
const CDPManager = require('./cdp-manager');
const LLMClient = require('./llm-client');
const CodeGenerator = require('./code-generator');
const db = require('./db');
const fs = require('fs').promises;
const path = require('path');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;

const program = new Command();

program
  .name('web-scraper')
  .description('AI-powered web scraping assistant')
  .version('1.0.0');

// Main scraping command
program
  .command('scrape')
  .description('Start the scraping workflow')
  .action(async () => {
    await runScrapingWorkflow();
  });

// CRUD commands
program
  .command('llms')
  .description('Manage LLM configurations')
  .action(async () => {
    await manageLLMs();
  });

program
  .command('codes')
  .description('Manage generated codes')
  .action(async () => {
    await manageCodes();
  });

program
  .command('runs')
  .description('View scraping runs')
  .action(async () => {
    await manageRuns();
  });

async function runScrapingWorkflow() {
  const cdp = new CDPManager();

  try {
    await cdp.connect();
    const targets = await cdp.listTargets();

    if (targets.length === 0) {
      console.log('No browser tabs found. Please open Chrome with --remote-debugging-port=9222');
      return;
    }

    console.log('Available tabs:');
    targets.forEach((target, index) => {
      console.log(`${index + 1}. ${target.title} - ${target.url}`);
    });

    const { choice } = await inquirer.prompt([
      {
        type: 'list',
        name: 'choice',
        message: 'Select a tab or enter a URL:',
        choices: [
          ...targets.map((target, index) => ({
            name: `${target.title} (${target.url})`,
            value: { type: 'tab', targetId: target.id, url: target.url }
          })),
          { name: 'Enter custom URL', value: { type: 'url' } }
        ]
      }
    ]);

    let targetId, url;
    if (choice.type === 'url') {
      const { customUrl } = await inquirer.prompt([
        {
          type: 'input',
          name: 'customUrl',
          message: 'Enter URL:',
          validate: input => input.startsWith('http') || 'URL must start with http'
        }
      ]);
      url = customUrl;
      // Create new tab for custom URL
      const { Target } = cdp.client;
      const { targetId: newTargetId } = await Target.createTarget({ url });
      targetId = newTargetId;
      // Wait a bit for page to load
      await new Promise(resolve => setTimeout(resolve, 2000));
    } else {
      targetId = choice.targetId;
      url = choice.url;
    }

    // Get HTML and accessibility snapshot
    const html = await cdp.getHTML(targetId);
    const axSnapshot = await cdp.getAccessibilitySnapshot(targetId);

    // Save data for debugging
    const htmlTimestamp = new Date().toISOString().replace(/[:.]/g, '-');
    await fs.mkdir('outputs', { recursive: true });
    await fs.writeFile(`outputs/html-${htmlTimestamp}.html`, html);
    await fs.writeFile(`outputs/ax-${htmlTimestamp}.json`, JSON.stringify(axSnapshot, null, 2));

    // Get LLM config
    const llms = db.prepare('SELECT * FROM llms').all();
    if (llms.length === 0) {
      console.log('No LLM configurations found. Please add one first.');
      return;
    }

    const { llmId } = await inquirer.prompt([
      {
        type: 'list',
        name: 'llmId',
        message: 'Select LLM for analysis:',
        choices: llms.map(llm => ({ name: llm.name, value: llm.id }))
      }
    ]);

    const llmConfig = llms.find(llm => llm.id === llmId);
    const llmClient = new LLMClient(llmConfig);
    const codeGen = new CodeGenerator(llmClient);

    // Analyze accessibility snapshot
    console.log('Analyzing page...');
    const suggestions = await llmClient.analyzeAccessibility(axSnapshot);

    // Save analysis for debugging
    const analysisData = {
      url,
      htmlLength: html.length,
      axNodesCount: axSnapshot.length,
      suggestions,
      timestamp: new Date().toISOString()
    };
    await fs.writeFile(`outputs/analysis-${htmlTimestamp}.json`, JSON.stringify(analysisData, null, 2));

    console.log('LLM suggestions:');
    suggestions.forEach((suggestion, index) => {
      console.log(`${index + 1}. ${suggestion.description} (${suggestion.selector})`);
    });

    const { confirmed } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'confirmed',
        message: 'Do these suggestions look good?',
        default: true
      }
    ]);

    if (!confirmed) {
      const { retry } = await inquirer.prompt([
        {
          type: 'confirm',
          name: 'retry',
          message: 'Retry analysis on the same page?',
          default: true
        }
      ]);
      if (retry) {
        // Retry analysis
        console.log('Retrying analysis...');
        const newSuggestions = await llmClient.analyzeAccessibility(axSnapshot);
        console.log('New suggestions:');
        newSuggestions.forEach((suggestion, index) => {
          console.log(`${index + 1}. ${suggestion.description} (${suggestion.selector})`);
        });
        const { newConfirmed } = await inquirer.prompt([
          {
            type: 'confirm',
            name: 'newConfirmed',
            message: 'Do these new suggestions look good?',
            default: true
          }
        ]);
        if (!newConfirmed) {
          console.log('Please try a different page or LLM.');
          return;
        }
        suggestions = newSuggestions;
      } else {
        console.log('Please try a different page or LLM.');
        return;
      }
    }

    // Generate code
    console.log('Generating scraping code...');
    const code = await codeGen.generateScrapingCode(html, suggestions, 'Extract all suggested data');

    // Save generated code for debugging
    await fs.writeFile(`outputs/code-${htmlTimestamp}.js`, code);

    console.log('Generated code:');
    console.log(code);

    const { codeConfirmed } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'codeConfirmed',
        message: 'Execute this code?',
        default: true
      }
    ]);

    if (!codeConfirmed) {
      console.log('Code rejected. Starting over.');
      return;
    }

    // Execute code
    console.log('Executing scraping code...');
    const data = await codeGen.executeCode(code, html);

    // Save scraped data for debugging
    await fs.writeFile(`outputs/data-${htmlTimestamp}.json`, JSON.stringify(data, null, 2));

    // Save to CSV
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const csvPath = path.join('outputs', `scrape-${timestamp}.csv`);

    await fs.mkdir('outputs', { recursive: true });

    const csvWriter = createCsvWriter({
      path: csvPath,
      header: Object.keys(data[0] || {}).map(key => ({ id: key, title: key }))
    });

    await csvWriter.writeRecords(data);

    // Save to database
    const htmlHash = require('crypto').createHash('md5').update(html).digest('hex');
    const insertCode = db.prepare('INSERT INTO generated_codes (html_hash, llm_id, code) VALUES (?, ?, ?)');
    const codeResult = insertCode.run(htmlHash, llmId, code);

    const insertRun = db.prepare('INSERT INTO runs (code_id, url, csv_path, status) VALUES (?, ?, ?, ?)');
    insertRun.run(codeResult.lastInsertRowid, url, csvPath, 'completed');

    console.log(`Data saved to ${csvPath}`);

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await cdp.disconnect();
  }
}

async function manageLLMs() {
  const { action } = await inquirer.prompt([
    {
      type: 'list',
      name: 'action',
      message: 'What would you like to do?',
      choices: ['List LLMs', 'Add LLM', 'Edit LLM', 'Delete LLM']
    }
  ]);

  switch (action) {
    case 'List LLMs':
      const llms = db.prepare('SELECT id, name, provider, model FROM llms').all();
      console.table(llms);
      break;
    case 'Add LLM':
      const answers = await inquirer.prompt([
        { type: 'input', name: 'name', message: 'Name:' },
        { type: 'list', name: 'provider', message: 'Provider:', choices: ['OpenAI', 'Anthropic'] },
        { type: 'input', name: 'api_key', message: 'API Key:' },
        { type: 'input', name: 'model', message: 'Model:' },
        { type: 'input', name: 'base_url', message: 'Base URL (optional):' }
      ]);
      db.prepare('INSERT INTO llms (name, provider, api_key, model, base_url) VALUES (?, ?, ?, ?, ?)').run(
        answers.name, answers.provider, answers.api_key, answers.model, answers.base_url || null
      );
      console.log('LLM added successfully');
      break;
    case 'Edit LLM':
      const editLlms = db.prepare('SELECT id, name FROM llms').all();
      if (editLlms.length === 0) {
        console.log('No LLMs to edit');
        break;
      }
      const { editId } = await inquirer.prompt([
        {
          type: 'list',
          name: 'editId',
          message: 'Select LLM to edit:',
          choices: editLlms.map(llm => ({ name: llm.name, value: llm.id }))
        }
      ]);
      const currentLLM = db.prepare('SELECT * FROM llms WHERE id = ?').get(editId);
      const editAnswers = await inquirer.prompt([
        { type: 'input', name: 'name', message: 'Name:', default: currentLLM.name },
        { type: 'list', name: 'provider', message: 'Provider:', choices: ['OpenAI', 'Anthropic'], default: currentLLM.provider },
        { type: 'input', name: 'api_key', message: 'API Key:', default: currentLLM.api_key },
        { type: 'input', name: 'model', message: 'Model:', default: currentLLM.model },
        { type: 'input', name: 'base_url', message: 'Base URL (optional):', default: currentLLM.base_url }
      ]);
      db.prepare('UPDATE llms SET name = ?, provider = ?, api_key = ?, model = ?, base_url = ? WHERE id = ?').run(
        editAnswers.name, editAnswers.provider, editAnswers.api_key, editAnswers.model, editAnswers.base_url || null, editId
      );
      console.log('LLM updated successfully');
      break;
    case 'Delete LLM':
      const deleteLlms = db.prepare('SELECT id, name FROM llms').all();
      if (deleteLlms.length === 0) {
        console.log('No LLMs to delete');
        break;
      }
      const { deleteId } = await inquirer.prompt([
        {
          type: 'list',
          name: 'deleteId',
          message: 'Select LLM to delete:',
          choices: deleteLlms.map(llm => ({ name: llm.name, value: llm.id }))
        }
      ]);
      const { confirmDelete } = await inquirer.prompt([
        { type: 'confirm', name: 'confirmDelete', message: 'Are you sure?', default: false }
      ]);
      if (confirmDelete) {
        db.prepare('DELETE FROM llms WHERE id = ?').run(deleteId);
        console.log('LLM deleted successfully');
      }
      break;
  }
}

async function manageCodes() {
  const { action } = await inquirer.prompt([
    {
      type: 'list',
      name: 'action',
      message: 'What would you like to do?',
      choices: ['List Codes', 'View Code', 'Delete Code']
    }
  ]);

  switch (action) {
    case 'List Codes':
      const codes = db.prepare('SELECT id, html_hash, created_at FROM generated_codes ORDER BY created_at DESC').all();
      console.table(codes);
      break;
    case 'View Code':
      const viewCodes = db.prepare('SELECT id, html_hash FROM generated_codes').all();
      if (viewCodes.length === 0) {
        console.log('No codes to view');
        break;
      }
      const { viewId } = await inquirer.prompt([
        {
          type: 'list',
          name: 'viewId',
          message: 'Select code to view:',
          choices: viewCodes.map(code => ({ name: `Code ${code.id} (${code.html_hash})`, value: code.id }))
        }
      ]);
      const code = db.prepare('SELECT code FROM generated_codes WHERE id = ?').get(viewId);
      console.log(code.code);
      break;
    case 'Delete Code':
      const deleteCodes = db.prepare('SELECT id, html_hash FROM generated_codes').all();
      if (deleteCodes.length === 0) {
        console.log('No codes to delete');
        break;
      }
      const { deleteCodeId } = await inquirer.prompt([
        {
          type: 'list',
          name: 'deleteCodeId',
          message: 'Select code to delete:',
          choices: deleteCodes.map(code => ({ name: `Code ${code.id}`, value: code.id }))
        }
      ]);
      const { confirmDeleteCode } = await inquirer.prompt([
        { type: 'confirm', name: 'confirmDeleteCode', message: 'Are you sure?', default: false }
      ]);
      if (confirmDeleteCode) {
        db.prepare('DELETE FROM generated_codes WHERE id = ?').run(deleteCodeId);
        console.log('Code deleted successfully');
      }
      break;
  }
}

async function manageRuns() {
  const { action } = await inquirer.prompt([
    {
      type: 'list',
      name: 'action',
      message: 'What would you like to do?',
      choices: ['List Runs', 'View Run Details']
    }
  ]);

  switch (action) {
    case 'List Runs':
      const runs = db.prepare(`
        SELECT r.id, r.url, r.status, r.created_at, c.html_hash
        FROM runs r
        JOIN generated_codes c ON r.code_id = c.id
        ORDER BY r.created_at DESC
      `).all();
      console.table(runs);
      break;
    case 'View Run Details':
      const viewRuns = db.prepare('SELECT id, url FROM runs').all();
      if (viewRuns.length === 0) {
        console.log('No runs to view');
        break;
      }
      const { viewRunId } = await inquirer.prompt([
        {
          type: 'list',
          name: 'viewRunId',
          message: 'Select run to view:',
          choices: viewRuns.map(run => ({ name: `Run ${run.id} (${run.url})`, value: run.id }))
        }
      ]);
      const run = db.prepare(`
        SELECT r.*, c.code
        FROM runs r
        JOIN generated_codes c ON r.code_id = c.id
        WHERE r.id = ?
      `).get(viewRunId);
      console.log('Run Details:');
      console.log(`URL: ${run.url}`);
      console.log(`Status: ${run.status}`);
      console.log(`CSV Path: ${run.csv_path}`);
      console.log(`Created: ${run.created_at}`);
      console.log('Code:');
      console.log(run.code);
      break;
  }
}

program.parse();