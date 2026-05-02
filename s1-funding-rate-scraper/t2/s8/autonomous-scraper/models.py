from pydantic import BaseModel
from typing import List, Literal, Optional


class FieldDefinition(BaseModel):
    field_name: str
    relative_selector: str
    extraction_type: Literal["text", "attribute", "href"]


class ExtractionSchema(BaseModel):
    item_selector: str
    fields: List[FieldDefinition]


class TargetConfig(BaseModel):
    name: str
    url: str
    prompt_instructions: str


class ScraperConfig(BaseModel):
    targets: List[TargetConfig]
    provider: str = "openai"  # "openai", "gemini", "anthropic", etc.
    llm_model: str = "gpt-4o"
    api_key_env_var: Optional[str] = None  # Environment variable name for API key
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None