# Content Automation System

A self-hostable platform for automated content creation and posting across multiple social media platforms.

## Features

- **Automated Content Gathering**: Collects information from RSS feeds, GitHub, Reddit, NewsAPI, and more
- **AI-Powered Content Generation**: Uses OpenAI or Anthropic LLMs to create engaging articles, social posts, and threads
- **Multi-Platform Posting**: Automatically posts to Twitter/X, Facebook, LinkedIn, and Instagram
- **Smart Scheduling**: Configurable scheduling with rate limiting and duplicate detection
- **Web Dashboard**: REST API for monitoring and managing content
- **CLI Interface**: Command-line tools for power users
- **Topic Coverage**: AI news, GitHub news, tech tutorials, AI in politics, AI in business, and practical AI applications

## Quick Start

### Prerequisites

- Python 3.10+
- (Optional) OpenAI or Anthropic API key for AI content generation
- (Optional) Social media API credentials for auto-posting

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/content-automation.git
cd content-automation

# Run setup wizard
python setup.py

# Or manual setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### Configuration

Edit `.env` file with your settings:

```env
# LLM API Keys (at least one required for AI content generation)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Social Media API Keys (optional, for auto-posting)
TWITTER_API_KEY=your_twitter_key
TWITTER_API_SECRET=your_twitter_secret
TWITTER_ACCESS_TOKEN=your_twitter_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_token_secret

FACEBOOK_ACCESS_TOKEN=your_facebook_token
LINKEDIN_ACCESS_TOKEN=your_linkedin_token
INSTAGRAM_ACCESS_TOKEN=your_instagram_token

# Data Source Keys (optional, for enhanced data collection)
GITHUB_TOKEN=your_github_token
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
NEWS_API_KEY=your_newsapi_key

# Application Settings
DATABASE_URL=sqlite:///./content_automation.db
DEFAULT_POST_INTERVAL_HOURS=6
MAX_POSTS_PER_DAY=4
```

## Usage

### Without API Keys (Fallback Mode)

The system works without any API keys using fallback content generation. It will:
- Collect data from public RSS feeds
- Generate basic content from collected data
- Store content in the database for review

### With LLM API Keys

When you configure OpenAI or Anthropic API keys, the system will:
- Generate high-quality, engaging content
- Create platform-optimized posts
- Generate Twitter/X threads
- Write comprehensive articles

### With Social Media Credentials

When you configure social media API credentials, the system will:
- Automatically post content on schedule
- Track posting status and errors
- Support multiple platforms simultaneously

## Running the Application

### Web Server

```bash
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### CLI Commands

```bash
# Show system status
python -m src.cli status

# Generate content manually
python -m src.cli generate --topic "ai news"

# Post scheduled content
python -m src.cli post --platforms "twitter,linkedin"

# List supported topics
python -m src.cli topics

# Show recent content
python -m src.cli recent --limit 20
```

## API Endpoints

Once running, access the API at `http://localhost:8000/api/v1/`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/content` | GET | List all content |
| `/content/{id}` | GET | Get specific content |
| `/content/generate` | POST | Trigger content generation |
| `/content/{id}/schedule` | POST | Schedule content for posting |
| `/content/post-now` | POST | Post all ready content immediately |
| `/posts` | GET | List all social media posts |
| `/stats` | GET | Get system statistics |
| `/topics` | GET | List supported topics |

Interactive API docs available at: `http://localhost:8000/docs`

## Architecture

```
content_automation/
├── src/
│   ├── main.py                 # FastAPI application entry point
│   ├── cli.py                  # Command-line interface
│   ├── core/
│   │   ├── config.py           # Configuration management
│   │   └── database.py         # Database setup
│   ├── models/
│   │   └── content.py          # SQLAlchemy models
│   ├── services/
│   │   ├── content_engine.py   # Main orchestration service
│   │   ├── data_collectors.py  # Data collection from various sources
│   │   ├── content_generator.py # LLM-powered content generation
│   │   ├── social_media_poster.py # Social media posting
│   │   └── scheduler.py        # Task scheduling
│   └── api/
│       ├── routes.py           # REST API endpoints
│       └── dashboard.py        # Web dashboard
├── requirements.txt
├── .env.example
├── setup.py
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## How It Works

1. **Data Collection**: The system continuously monitors RSS feeds, GitHub trending, Reddit, and news APIs for content related to your topics
2. **Content Generation**: An LLM analyzes the collected data and creates engaging articles, social posts, and threads
3. **Scheduling**: Content is automatically scheduled for posting at optimal intervals
4. **Posting**: The system posts to your configured social media platforms
5. **Monitoring**: Track all content and posts through the web dashboard or CLI

## Supported Topics

- AI News
- GitHub News
- Tech Tutorials
- AI Applied to Politics
- AI Applied to Business
- Real Value AI (practical applications)

## Deployment

### Self-Hosted with Docker

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Managed Instance

For a managed hosting solution, contact us at [your-email@example.com]

## Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest

# Format code
black src/

# Lint code
flake8 src/
```

## License

MIT License - see LICENSE file for details