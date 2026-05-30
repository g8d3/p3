"""Hugging Face connector — trending models + inference."""
from __future__ import annotations
import json
import urllib.request
from typing import Any, Dict, List
from .base import SourceConnector


class HuggingFaceConnector(SourceConnector):
    """Fetches trending models, datasets, and runs inference.

    - Trending models (daily/weekly)
    - Trending datasets
    - Optional: run inference on a text-generation model
    """

    name = "huggingface"
    INFERENCE_URL = "https://api-inference.huggingface.co/models/"

    def _do_fetch(self) -> List[Dict[str, Any]]:
        items = []
        # Trending models
        url = "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=10"
        req = urllib.request.Request(url, headers={"User-Agent": "ai-video-studio/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                models = json.loads(r.read())
                for m in models:
                    items.append({
                        "source": "huggingface",
                        "type": "model",
                        "title": m.get("modelId", ""),
                        "description": m.get("pipeline_tag", ""),
                        "url": f"https://huggingface.co/{m.get('modelId', '')}",
                        "downloads": m.get("downloads", 0),
                        "likes": m.get("likes", 0),
                        "tags": m.get("tags", []),
                    })
        except Exception as e:
            self._last_error = f"Models fetch: {e}"

        # Trending datasets
        try:
            url2 = "https://huggingface.co/api/datasets?sort=downloads&direction=-1&limit=5"
            req2 = urllib.request.Request(url2, headers={"User-Agent": "ai-video-studio/1.0"})
            with urllib.request.urlopen(req2, timeout=15) as r:
                dsets = json.loads(r.read())
                for d in dsets:
                    items.append({
                        "source": "huggingface",
                        "type": "dataset",
                        "title": d.get("id", ""),
                        "description": d.get("description", "")[:200],
                        "url": f"https://huggingface.co/datasets/{d.get('id', '')}",
                        "downloads": d.get("downloads", 0),
                    })
        except Exception as e:
            self._last_error += f" | Datasets fetch: {e}"

        return items

    def infer(self, model: str, prompt: str, **kwargs) -> str:
        """Run inference on a HF model (requires API key)."""
        if not self.api_key:
            return "API key required for inference."
        import requests
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"inputs": prompt, **kwargs}
        try:
            resp = requests.post(
                f"{self.INFERENCE_URL}{model}",
                headers=headers, json=payload, timeout=30,
            )
            return resp.json()
        except Exception as e:
            return f"Inference error: {e}"
