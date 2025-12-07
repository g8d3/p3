import base64
import json
import logging
from pathlib import Path
from typing import Optional

import requests
from openai import OpenAI
from playwright.sync_api import sync_playwright

from models import ExtractionSchema, ScraperConfig


logger = logging.getLogger(__name__)


class VisualDiscovery:
    def __init__(self, config: ScraperConfig):
        self.config = config
        if not config.api_key:
            env_var = config.api_key_env_var or f"{config.provider.upper()}_API_KEY"
            raise ValueError(f"API key is required. Set {env_var} environment variable or configure in config.yaml")

        self.client = self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate LLM client based on provider."""
        provider_initializers = {
            'openai': self._initialize_openai_client,
            'gemini': self._initialize_gemini_client,
            'anthropic': self._initialize_anthropic_client,
        }

        initializer = provider_initializers.get(self.config.provider.lower())
        if not initializer:
            supported = list(provider_initializers.keys())
            raise ValueError(f"Unsupported provider: {self.config.provider}. Supported: {', '.join(supported)}")

        return initializer()

    def _initialize_openai_client(self):
        """Initialize OpenAI client."""
        try:
            import openai
            client_kwargs = {"api_key": self.config.api_key}
            if self.config.api_base_url:
                client_kwargs["base_url"] = self.config.api_base_url
            return openai.OpenAI(**client_kwargs)
        except ImportError:
            raise ImportError("openai package required for OpenAI provider. Install with: pip install openai")

    def _initialize_gemini_client(self):
        """Initialize Gemini client."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.config.api_key)
            return genai.GenerativeModel(self.config.llm_model)
        except ImportError:
            raise ImportError("google-generativeai package required for Gemini provider. Install with: pip install google-generativeai")

    def _initialize_anthropic_client(self):
        """Initialize Anthropic client."""
        try:
            from anthropic import Anthropic
            return Anthropic(api_key=self.config.api_key)
        except ImportError:
            raise ImportError("anthropic package required for Anthropic provider. Install with: pip install anthropic")

    def capture_page_data(self, url: str) -> tuple[str, str]:
        """Capture screenshot and HTML from the target URL."""
        screenshot_path = Path("temp_screenshot.png")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
                context = browser.new_context()
                page = context.new_page()

                try:
                    page.goto(url, timeout=60000, wait_until='domcontentloaded')
                    page.wait_for_load_state('networkidle', timeout=60000)

                    # Take screenshot
                    page.screenshot(path=screenshot_path, full_page=True)

                    # Get HTML
                    html_content = page.content()

                    # Convert screenshot to base64
                    with open(screenshot_path, "rb") as f:
                        screenshot_b64 = base64.b64encode(f.read()).decode()

                    return html_content, screenshot_b64

                finally:
                    context.close()
                    browser.close()

        except Exception as e:
            logger.error(f"Error capturing page data for {url}: {e}")
            raise
        finally:
            # Clean up screenshot file
            if screenshot_path.exists():
                screenshot_path.unlink()

    def generate_schema(self, url: str, prompt_instructions: str) -> tuple[ExtractionSchema, str]:
        """Generate extraction schema using LLM analysis of page visual structure.
        Returns both the schema and the HTML content for reuse."""
        html_content, screenshot_b64 = self.capture_page_data(url)

        prompt = f"""
        Analyze the provided webpage screenshot and HTML to identify repeating item containers.

        {prompt_instructions}

        Your response must be ONLY the JSON object defined below, with no surrounding prose or markdown formatting:

        {{
            "item_selector": "CSS selector for the repeating parent element",
            "fields": [
                {{
                    "field_name": "name of the field",
                    "relative_selector": "CSS selector relative to item_selector",
                    "extraction_type": "text|attribute|href"
                }}
            ]
        }}
        """

        response = self.client.chat.completions.create(
            model=self.config.llm_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}
                        }
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.1
        )

        schema_json = response.choices[0].message.content.strip()

        # Parse and validate the schema
        try:
            schema_data = json.loads(schema_json)
            schema = ExtractionSchema(**schema_data)
            return schema, html_content
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise ValueError("LLM returned invalid schema format")