"""Base agent class."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class AgentBase(ABC):
    """Abstract base class for agents."""
    
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = []
        self.memory = []
    
    @abstractmethod
    def run(self, user_input: str, context: Optional[List[Dict]] = None) -> str:
        """Run the agent with user input."""
        pass
    
    def add_tool(self, tool: "Tool"):
        """Add a tool to the agent."""
        self.tools.append(tool)
    
    def clear_memory(self):
        """Clear agent memory."""
        self.memory = []
    
    def get_system_prompt(self) -> str:
        """Get the system prompt."""
        return self.system_prompt
