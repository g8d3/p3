# Autonomous Hybrid Web Scraper

A production-ready web scraper using a hybrid two-phase architecture: Visual Discovery (LLM + Playwright) followed by Traditional Extraction (BeautifulSoup).

## Features

- **Two-Phase Architecture**: Visual discovery using multimodal LLM followed by fast HTML extraction
- **Robust Schema Generation**: LLM analyzes page screenshots to identify repeating item containers
- **Configurable Targets**: Define scraping targets in YAML configuration
- **Comprehensive Logging**: Track scraping progress, errors, and performance metrics
- **Clean Data Output**: Export results to JSON or CSV formats

## Installation

1. Clone or download this repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```bash
   playwright install
   ```
4. Set up your OpenAI API key in `config.yaml`

## Configuration

### Environment Variables (Required)

Set your API credentials using environment variables:

```bash
# Required: Specify provider and API key
export PROVIDER="gemini"  # or "openai", "anthropic", etc.
export GEMINI_API_KEY="your-gemini-api-key-here"  # Use any env var name you want
export API_KEY_ENV_VAR="GEMINI_API_KEY"  # Tell the scraper which env var contains the key

# Optional: Model and endpoint settings
export LLM_MODEL="gemini-pro-vision"  # Model name (provider-specific)
export API_BASE_URL="https://api.openai.com/v1"  # Optional: for custom endpoints
```

### Supported Providers

- **OpenAI**: `openai` (models: gpt-4o, gpt-4-turbo, etc.)
- **Gemini**: `gemini` (models: gemini-pro-vision, gemini-pro, etc.)
- **Anthropic**: `anthropic` (models: claude-3-opus, claude-3-sonnet, etc.)

### Configuration File

Edit `config.yaml` to define your scraping targets:

```yaml
# API credentials can be set via environment variables (recommended)
# provider: "gemini"  # Can be set via PROVIDER env var
# api_key_env_var: "GEMINI_API_KEY"  # Can be set via API_KEY_ENV_VAR env var
# llm_model: "gemini-pro-vision"  # Can be set via LLM_MODEL env var
# api_base_url: "https://api.openai.com/v1"  # Can be set via API_BASE_URL env var

targets:
  - name: "my_target"
    url: "https://example.com"
    prompt_instructions: |
      Describe what to extract from this page...
```

### Setting Environment Variables

#### Temporary (current session only):
```bash
export PROVIDER="gemini"
export GEMINI_API_KEY="your-key-here"
export API_KEY_ENV_VAR="GEMINI_API_KEY"
export LLM_MODEL="gemini-pro-vision"
python main.py
```

#### Permanent (add to your shell profile):
```bash
echo 'export PROVIDER="gemini"' >> ~/.bashrc
echo 'export GEMINI_API_KEY="your-key-here"' >> ~/.bashrc
echo 'export API_KEY_ENV_VAR="GEMINI_API_KEY"' >> ~/.bashrc
echo 'export LLM_MODEL="gemini-pro-vision"' >> ~/.bashrc
source ~/.bashrc
```

#### Using Different API Key Variables:
```bash
# You can use any environment variable name
export PROVIDER="openai"
export MY_CUSTOM_API_KEY="sk-..."
export API_KEY_ENV_VAR="MY_CUSTOM_API_KEY"
```

## Usage

Run the scraper for all targets:
```bash
python main.py
```

Run for a specific target:
```bash
python main.py --target=my_target
```

Use a custom config file:
```bash
python main.py --config=my_config.yaml
```

## Architecture

### Phase 1: Visual Discovery
- Uses Playwright to capture page screenshots and HTML
- Multimodal LLM analyzes visual structure to identify repeating containers
- Generates extraction schema with CSS selectors

### Phase 2: Automated Extraction
- Uses BeautifulSoup for fast HTML parsing
- Applies generated schema to extract structured data
- Outputs clean JSON/CSV files

## Requirements

- Python 3.10+
- OpenAI API key with access to GPT-4 Vision
- Playwright browsers installed

## Output

Results are saved as JSON files named `output_{target_name}_{timestamp}.json` in the current directory.