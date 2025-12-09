# BizBot - Autonomous Business Agent MVP

BizBot is an agent designed to autonomously create, acquire (scout), and maintain online businesses.
This MVP focuses on the **Create -> Deploy -> Market** loop for digital products and micro-SaaS.

## Features

- **Idea Scout**: Scrapes Reddit (r/sidehustle) and X (Trending/Search) for ideas.
- **Product Generator**: Uses LLMs (`GPT-4o` / `Claude 3.5`) to generate E-books (PDF) or Code Tools (Zip).
- **Marketing Loop**: Auto-generates tweets and posts them to X using a browser automation (Playwright).
- **Control Dashboard**: A web interface to review ideas and track assets.

## Setup

1.  **Install Dependencies**:
    ```bash
    npm install
    ```

2.  **Environment Variables**:
    Set `OPENAI_API_KEY` in your environment.
    ```bash
    export OPENAI_API_KEY=sk-...
    ```

3.  **Browser Setup** (Critical):
    To enable X posting and effective scraping, run Chrome with a remote debugging port:
    ```bash
    google-chrome --remote-debugging-port=9222
    ```
    Log in to X.com in this browser window.

## Usage

### 1. Scout for Ideas
Find new ideas from Reddit and X:
```bash
node scrapers/reddit_scraper.js
node scrapers/x_scraper.js
```

### 2. Dashboard
Start the command center to view ideas and assets:
```bash
node dashboard/server.js
```
Open [http://localhost:3000](http://localhost:3000).

### 3. Generate Products
Click "Generate Product" in the dashboard, or run manually:
```bash
node generators/product_maker.js
```
Artifacts are saved to `products/`.

### 4. Run Marketing
Post updates about new assets to X:
```bash
node marketing/marketer.js
```

## Architecture

- **Database**: SQLite (`data.db`)
- **Scrapers**: Playwright (CDP mode preferred)
- **Generators**: PDFKit, Archiver, OpenAI API
- **Marketing**: Playwright Automation
