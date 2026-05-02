"""Agent implementation."""

from typing import Dict, List, Optional, Any
from datetime import datetime

from agents.base import AgentBase


class ConversationalAgent(AgentBase):
    """Standard conversational agent."""
    
    def __init__(self, name: str, system_prompt: str, provider, model: str):
        super().__init__(name, system_prompt)
        self.provider = provider
        self.model = model
        self.max_history = 50
    
    def run(self, user_input: str, context: Optional[List[Dict]] = None) -> str:
        """Run the conversational agent."""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        for msg in self.memory[-self.max_history:]:
            messages.append(msg)
        
        if context:
            messages.extend(context)
        
        messages.append({"role": "user", "content": user_input})
        
        response, usage = self.provider.chat(messages, self.model)
        
        self.memory.append({"role": "user", "content": user_input})
        self.memory.append({"role": "assistant", "content": response})
        
        return response
    
    def add_to_memory(self, role: str, content: str):
        """Add a message to memory."""
        self.memory.append({"role": role, "content": content})
    
    def get_history(self) -> List[Dict]:
        """Get conversation history."""
        return self.memory.copy()


class ToolCallingAgent(AgentBase):
    """Agent that can use tools."""
    
    def __init__(self, name: str, system_prompt: str, provider, model: str):
        super().__init__(name, system_prompt)
        self.provider = provider
        self.model = model
        self.max_history = 50
    
    def run(self, user_input: str, context: Optional[List[Dict]] = None) -> str:
        """Run the agent with tool support."""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        for msg in self.memory[-self.max_history:]:
            messages.append(msg)
        
        if context:
            messages.extend(context)
        
        messages.append({"role": "user", "content": user_input})
        
        response, usage = self.provider.chat(messages, self.model)
        
        self.memory.append({"role": "user", "content": user_input})
        self.memory.append({"role": "assistant", "content": response})
        
        return response
    
    def execute_tool(self, tool_name: str, args: Dict) -> str:
        """Execute a tool."""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool.execute(args)
        return f"Tool not found: {tool_name}"
