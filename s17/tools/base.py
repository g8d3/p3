"""Base tool class."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class ToolBase(ABC):
    """Abstract base class for tools."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, args: Dict[str, Any]) -> str:
        """Execute the tool with given arguments."""
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict:
        """Get the parameters schema for the tool."""
        pass
    
    def validate_args(self, args: Dict) -> bool:
        """Validate tool arguments."""
        params = self.get_parameters()
        required = params.get("required", [])
        
        for req in required:
            if req not in args:
                return False
        
        return True
