import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

from discovery import VisualDiscovery
from extractor import DataExtractor
from models import ScraperConfig, TargetConfig


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scraper.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_config(config_path: str) -> ScraperConfig:
    """Load configuration from YAML file and environment variables."""
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)

    # Override with environment variables if they exist
    if 'PROVIDER' in os.environ:
        config_data['provider'] = os.environ['PROVIDER']

    if 'LLM_MODEL' in os.environ:
        config_data['llm_model'] = os.environ['LLM_MODEL']

    if 'API_KEY_ENV_VAR' in os.environ:
        config_data['api_key_env_var'] = os.environ['API_KEY_ENV_VAR']

    if 'API_BASE_URL' in os.environ:
        config_data['api_base_url'] = os.environ['API_BASE_URL']

    # Load API key from specified environment variable
    api_key_env_var = config_data.get('api_key_env_var')
    if api_key_env_var and api_key_env_var in os.environ:
        config_data['api_key'] = os.environ[api_key_env_var]
    elif not api_key_env_var:
        # Auto-detect based on provider if no specific env var set
        provider = config_data.get('provider', 'openai')
        default_env_vars = {
            'openai': 'OPENAI_API_KEY',
            'gemini': 'GEMINI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'groq': 'GROQ_API_KEY',
            'together': 'TOGETHER_API_KEY',
        }
        default_var = default_env_vars.get(provider.lower(), f'{provider.upper()}_API_KEY')
        if default_var in os.environ:
            config_data['api_key'] = os.environ[default_var]

    return ScraperConfig(**config_data)


def run_scraper(target: TargetConfig, config: ScraperConfig):
    """Run the scraper for a single target."""
    logger = logging.getLogger(__name__)

    start_time = time.time()

    try:
        logger.info(f"Starting scraping for target: {target.name}")

        # Phase 1: Visual Discovery
        discovery = VisualDiscovery(config)
        schema, html_content = discovery.generate_schema(target.url, target.prompt_instructions)

        logger.info(f"Generated schema: {schema.model_dump_json()}")

        # Phase 2: Data Extraction
        extractor = DataExtractor(schema)
        data = extractor.extract_data(html_content)

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"output_{target.name}_{timestamp}.json"

        # Save data
        extractor.save_to_json(data, output_filename)

        end_time = time.time()
        duration = end_time - start_time

        logger.info(f"Successfully scraped {len(data)} items for {target.name}")
        logger.info(f"Output saved to {output_filename}")
        logger.info(f"Total time: {duration:.2f} seconds")

    except Exception as e:
        logger.error(f"Failed to scrape {target.name}: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description='Autonomous Hybrid Web Scraper')
    parser.add_argument('--config', default='config.yaml', help='Path to config file')
    parser.add_argument('--target', help='Specific target to scrape (optional)')

    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        config = load_config(args.config)
        logger.info("Configuration loaded successfully")

        targets_to_run = config.targets
        if args.target:
            targets_to_run = [t for t in config.targets if t.name == args.target]
            if not targets_to_run:
                logger.error(f"Target '{args.target}' not found in config")
                sys.exit(1)

        for target in targets_to_run:
            run_scraper(target, config)

    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()