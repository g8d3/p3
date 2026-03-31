# AutoContent - Automated Content Creation System

A fully automated content creation system that scrapes X.com likes/bookmarks, generates content using LLM, creates videos, and pushes code to GitHub PRs.

## Features

- **X.com Scraping**: Automatically scrapes likes and bookmarks from X.com
- **LLM Content Generation**: Uses OpenAI/Anthropic/Ollama to generate content
- **Video Creation**: Creates videos from generated scripts using ffmpeg
- **GitHub PRs**: Creates pull requests with generated code
- **Auto-Provisioning**: Automatically sets up required accounts
- **Scheduling**: Runs content creation on a schedule
- **Self-Healing**: Automatically retries and recovers from errors
- **Verification**: Verifies inputs and outputs

## Requirements

### User Requirements (Only these needed)
1. **LLM Access**: OpenAI API key, Anthropic API key, or Ollama
2. **CDP Browser**: Chrome DevTools Protocol browser (via agent-browser)
3. **Wallet/Debit Card**: For future payment integrations

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...  # Or ANTHROPIC_API_KEY

# X.com (for scraping)
X_USERNAME=your_username
X_PASSWORD=your_password

# GitHub (for PRs)
GITHUB_TOKEN=ghp_...

# Optional
WALLET_API_KEY=...
CARD_TOKEN=...
```

## Installation

```bash
pip install -r requirements.txt

# Install system dependencies
# - ffmpeg (for video generation)
# - espeak or gtts (for text-to-speech)
```

## Usage

### Single Run
```bash
python main.py
```

### Scheduled Mode
```bash
python main.py --schedule
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AutoContent Orchestrator                 │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ X Scraper│  │   LLM    │  │  Video   │  │  GitHub  │   │
│  │          │  │Processor │  │Generator │  │  Manager │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Provisioner│ │ Scheduler│  │  Error   │  │  Logger  │   │
│  │          │  │          │  │ Handler  │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Components

| Module | Description |
|--------|-------------|
| `config.py` | Configuration management |
| `logger.py` | Centralized logging with error tracking |
| `error_handler.py` | Self-healing error handling |
| `x_scraper.py` | X.com likes/bookmarks scraper |
| `llm_processor.py` | LLM content generation |
| `video_generator.py` | Video creation from scripts |
| `github_manager.py` | GitHub PR creation |
| `provisioner.py` | Auto-provisioning of accounts |
| `scheduler.py` | Task scheduling |
| `main.py` | Main orchestrator |

## Workflow

1. **Provision**: Check/verify all required services
2. **Scrape**: Get likes and bookmarks from X.com
3. **Generate**: Use LLM to create content, scripts, code
4. **Create**: Generate video from script
5. **Push**: Create GitHub PR with code
6. **Schedule**: Repeat on configured interval

## Verification & Self-Healing

- **Input Verification**: Validates X credentials, API keys
- **Output Verification**: Checks scraped posts, generated videos
- **Self-Healing**: Automatic retry with strategies:
  - Retry with exponential backoff
  - Browser restart
  - Session refresh
  - LLM fallback

## License

MIT
