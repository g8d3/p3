"""Base template class and public rendering API."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..models import TemplateConfig


class VideoTemplate(ABC):
    """Abstract base for all video templates.

    Subclasses define a specific visual style (layout, fonts, effects).
    """

    def __init__(self, config: Optional[TemplateConfig] = None):
        self.config = config or TemplateConfig(name=self.__class__.__name__)

    @abstractmethod
    async def render(self, **kwargs) -> str:
        """Render the template to a video file.

        Returns:
            Path to the rendered video file.
        """
        ...
