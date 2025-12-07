import json
import logging
from typing import List, Dict, Any

from bs4 import BeautifulSoup

from models import ExtractionSchema


logger = logging.getLogger(__name__)


class DataExtractor:
    def __init__(self, schema: ExtractionSchema):
        self.schema = schema

    def extract_data(self, html_content: str) -> List[Dict[str, Any]]:
        """Extract data from HTML using the provided schema."""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find all item containers
        items = soup.select(self.schema.item_selector)

        extracted_data = []

        for item in items:
            item_data = {}

            for field in self.schema.fields:
                try:
                    element = item.select_one(field.relative_selector)
                    if element:
                        if field.extraction_type == "text":
                            value = element.get_text(strip=True)
                        elif field.extraction_type == "attribute":
                            # For attributes, we'll assume 'src' or similar common attributes
                            # In a real implementation, you might want to specify which attribute
                            value = element.get('src') or element.get('href') or element.get('alt')
                        elif field.extraction_type == "href":
                            value = element.get('href')
                        else:
                            value = None

                        item_data[field.field_name] = value
                    else:
                        item_data[field.field_name] = None

                except Exception as e:
                    logger.warning(f"Error extracting field {field.field_name}: {e}")
                    item_data[field.field_name] = None

            if item_data:  # Only add if we extracted some data
                extracted_data.append(item_data)

        return extracted_data

    def save_to_json(self, data: List[Dict[str, Any]], filename: str):
        """Save extracted data to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_to_csv(self, data: List[Dict[str, Any]], filename: str):
        """Save extracted data to CSV file."""
        import csv

        if not data:
            return

        fieldnames = data[0].keys()

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)