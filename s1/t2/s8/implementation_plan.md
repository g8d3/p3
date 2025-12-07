# Implementation Plan for Web Scraping Assistant

## Architecture Overview
This application will be built as a Node.js CLI tool with a modular architecture separating concerns into CDP interaction, LLM integration, code generation, data storage, and user interface components.

## Core Components

### 1. CDP Manager (`cdp-manager.js`)
- Uses `chrome-remote-interface` library to connect to CDP on port 9222
- Provides methods to:
  - List available browser tabs/targets
  - Navigate to URLs
  - Extract page HTML content
  - Execute JavaScript for scraping

### 2. LLM Integration (`llm-client.js`)
- Generic LLM client supporting multiple providers (OpenAI, Anthropic, local models)
- Configuration stored in JSON file with API keys, models, base URLs
- Methods for:
  - Analyzing HTML content
  - Generating scraping suggestions
  - Creating scraping code from user confirmation

### 3. Code Generator (`code-generator.js`)
- Uses LLM to generate Node.js scraping code
- Templates for common scraping patterns (cheerio, puppeteer)
- Validation and testing of generated code

### 4. Data Storage Layer
- **Database**: SQLite with tables for:
  - `llms` (id, name, provider, api_key, model, base_url)
  - `generated_codes` (id, html_hash, llm_id, code, created_at)
  - `runs` (id, code_id, url, csv_path, status, created_at)
- **Filesystem**: JSON files for workflows and configurations
- Uses `better-sqlite3` for database operations

### 5. User Interface (`cli.js`)
- Interactive CLI using `inquirer` for user prompts
- Workflow management (save/load scraping sessions)
- CRUD operations for LLMs, codes, and runs

## Workflow Implementation

### Main Loop
1. Connect to CDP and display available tabs
2. User selects tab or enters URL → navigate and get HTML
3. Send HTML to configured LLM for analysis
4. LLM suggests scraping targets → user confirms/rejects
5. If accepted: LLM generates scraping code
6. Execute code, save results to CSV → user reviews
7. If accepted: save run record and return to step 1

### CRUD Interfaces
- **LLMs**: Add/edit/remove LLM configurations
- **Codes**: View/edit generated scraping code
- **Runs**: Browse execution history with CSV outputs

## Technology Stack
- **Runtime**: Node.js 18+
- **CDP**: chrome-remote-interface
- **LLM**: openai, @anthropic-ai/sdk (configurable)
- **Database**: better-sqlite3
- **Scraping**: cheerio for HTML parsing
- **CLI**: commander, inquirer
- **File Storage**: Node.js fs/promises for JSON workflows

## Data Flow
```
User Input → CDP → HTML → LLM Analysis → User Confirmation → Code Generation → Execution → CSV Output → Database Record
```

## Configuration
- `config.json`: Application settings, database path
- `workflows/`: Directory for saved scraping workflows
- `outputs/`: Directory for CSV files and logs

## Security Considerations
- API keys stored encrypted in database
- Input validation for URLs and user inputs
- Sandboxed code execution for generated scrapers

## Development Approach
1. Start with CDP connection and tab listing
2. Add LLM integration with mock responses
3. Implement code generation and execution
4. Build CRUD interfaces
5. Add workflow persistence
6. Testing and error handling