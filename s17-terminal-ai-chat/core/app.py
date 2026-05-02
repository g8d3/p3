"""Main application class."""

import sys
import os
import json
import uuid
import curses
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from core.database import Database, Provider, Model, Agent, Session, Message, Tool, Schedule, APILog
from core.config import AppConfig
from core.ui import UITerminal

from providers.base import Provider as BaseProvider
from providers.openai import OpenAIProvider
from providers.anthropic import AnthropicProvider
from providers.ollama import OllamaProvider


class TerminalAIApp:
    """Main terminal AI application."""
    
    def __init__(self):
        self.config = AppConfig.load()
        self.db = Database(self.config.database_path)
        self.ui = UITerminal()
        
        self.current_session: Optional[Session] = None
        self.current_agent: Optional[Agent] = None
        
        self.providers: Dict[str, BaseProvider] = {}
        self.tool_registry: Dict[str, Any] = {}
        
        self._init_providers()
        self._init_default_data()
    
    def _init_providers(self):
        """Initialize provider instances."""
        db_providers = self.db.get_providers()
        
        for db_provider in db_providers:
            if not db_provider.enabled:
                continue
            
            provider = self._create_provider(db_provider)
            if provider:
                self.providers[db_provider.name] = provider
    
    def _create_provider(self, db_provider: Provider) -> Optional[BaseProvider]:
        """Create provider instance from database provider."""
        provider_type = db_provider.provider_type.lower()
        
        config = {
            "name": db_provider.name,
            "api_key": db_provider.api_key,
            "base_url": db_provider.base_url,
            "extra": json.loads(db_provider.extra) if db_provider.extra else {}
        }
        
        if provider_type == "openai":
            return OpenAIProvider(config)
        elif provider_type == "anthropic":
            return AnthropicProvider(config)
        elif provider_type == "ollama":
            return OllamaProvider(config)
        elif provider_type == "local":
            from providers.local import LocalProvider
            return LocalProvider(config)
        
        return None
    
    def _init_default_data(self):
        """Initialize default providers and models if none exist."""
        if not self.db.get_providers():
            self._create_default_providers()
        
        if not self.db.get_models():
            self._create_default_models()
        
        if not self.db.get_agents():
            self._create_default_agents()
    
    def _create_default_providers(self):
        """Create default provider configurations."""
        default_providers = [
            Provider(
                id=str(uuid.uuid4()),
                name="openai",
                provider_type="openai",
                api_key=os.environ.get("OPENAI_API_KEY"),
                base_url="https://api.openai.com/v1",
                enabled=True,
                extra="{}",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            Provider(
                id=str(uuid.uuid4()),
                name="anthropic",
                provider_type="anthropic",
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
                base_url="https://api.anthropic.com",
                enabled=True,
                extra="{}",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            Provider(
                id=str(uuid.uuid4()),
                name="ollama",
                provider_type="ollama",
                api_key=None,
                base_url="http://localhost:11434",
                enabled=True,
                extra="{}",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
        ]
        
        for provider in default_providers:
            self.db.create_provider(provider)
    
    def _create_default_models(self):
        """Create default model configurations."""
        default_models = [
            Model(
                id=str(uuid.uuid4()),
                name="GPT-4",
                provider_name="openai",
                model_id="gpt-4",
                context_window=128000,
                max_tokens=8192,
                cost_per_input=0.03,
                cost_per_output=0.06,
                is_default=True,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            Model(
                id=str(uuid.uuid4()),
                name="GPT-4o",
                provider_name="openai",
                model_id="gpt-4o",
                context_window=128000,
                max_tokens=16384,
                cost_per_input=0.005,
                cost_per_output=0.015,
                is_default=False,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            Model(
                id=str(uuid.uuid4()),
                name="Claude 3.5 Sonnet",
                provider_name="anthropic",
                model_id="claude-3-5-sonnet-20241022",
                context_window=200000,
                max_tokens=8192,
                cost_per_input=0.003,
                cost_per_output=0.015,
                is_default=True,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            Model(
                id=str(uuid.uuid4()),
                name="Llama 3.1 70B",
                provider_name="ollama",
                model_id="llama3.1:70b",
                context_window=131072,
                max_tokens=8192,
                cost_per_input=0.0,
                cost_per_output=0.0,
                is_default=False,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            Model(
                id=str(uuid.uuid4()),
                name="Llama 3.2 3B",
                provider_name="ollama",
                model_id="llama3.2:3b",
                context_window=131072,
                max_tokens=8192,
                cost_per_input=0.0,
                cost_per_output=0.0,
                is_default=False,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
        ]
        
        for model in default_models:
            try:
                self.db.create_model(model)
            except Exception:
                pass
    
    def _create_default_agents(self):
        """Create default agent configurations."""
        default_agents = [
            Agent(
                id=str(uuid.uuid4()),
                name="general",
                system_prompt="You are a helpful AI assistant. Be concise, clear, and helpful.",
                provider_name="openai",
                model_name="GPT-4o",
                tools="[]",
                enabled=True,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            Agent(
                id=str(uuid.uuid4()),
                name="coder",
                system_prompt="You are an expert software developer. Help with code, explain concepts, and write clean, well-documented code. Specialize in Python, JavaScript, and general programming patterns.",
                provider_name="openai",
                model_name="GPT-4",
                tools="[]",
                enabled=True,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
            Agent(
                id=str(uuid.uuid4()),
                name="analyst",
                system_prompt="You are a data analyst. Help analyze data, create visualizations, and provide insights. Be thorough and explain your methodology.",
                provider_name="anthropic",
                model_name="Claude 3.5 Sonnet",
                tools="[]",
                enabled=True,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            ),
        ]
        
        for agent in default_agents:
            try:
                self.db.create_agent(agent)
            except Exception:
                pass
    
    def run(self):
        """Run the main application loop."""
        self.ui.init_screen()
        
        try:
            self.ui.setup_panels(curses.LINES, curses.COLS)
            self.ui.ready = True
            
            if not self.db.get_sessions():
                self._create_new_session()
            else:
                sessions = self.db.get_sessions()
                self.current_session = sessions[0]
            
            self._main_loop()
        finally:
            self.ui.cleanup()
    
    def _main_loop(self):
        """Main application loop."""
        self.ui.stdscr.nodelay(True)
        timeout_ms = 100

        while True:
            self._render()

            key = self.ui.stdscr.getch()

            if key == curses.ERR:
                if self.ui.key_queue:
                    key = self.ui.key_queue.pop(0)
                else:
                    continue

            if key == ord('/'):
                self._handle_command()
            elif key == ord('c'):
                self._clear_chat()
            elif key == ord('s'):
                self._switch_session()
            elif key == ord('a'):
                self._select_agent()
            elif key == ord('m'):
                self._select_model()
            elif key == ord('p'):
                self._manage_providers()
            elif key == ord('g'):
                self._manage_agents()
            elif key == ord('t'):
                self._manage_tools()
            elif key == ord('h'):
                self._show_help()
            elif key == ord('q'):
                break
            elif key == ord('n'):
                self._create_new_session()
            elif key in (ord('?'), curses.KEY_F1):
                self._show_help()
            elif self.current_session:
                if key in (10, 13):
                    self._handle_user_input()
    
    def _render(self):
        """Render UI."""
        self.ui.clear()
        
        if self.current_session:
            messages = self.db.get_messages(self.current_session.id)
            self.ui.chat_panel.clear_chat()
            
            for msg in messages:
                metadata = {}
                if msg.tokens_in:
                    metadata["tokens_in"] = msg.tokens_in
                if msg.tokens_out:
                    metadata["tokens_out"] = msg.tokens_out
                if msg.latency_ms:
                    metadata["latency_ms"] = msg.latency_ms
                if msg.ttft_ms:
                    metadata["ttft_ms"] = msg.ttft_ms
                if msg.cost:
                    metadata["cost"] = msg.cost
                
                self.ui.chat_panel.add_message(msg.role, msg.content, metadata if metadata else None)
            
            stats = self.db.get_session_stats(self.current_session.id)
            if stats:
                for key, value in stats.items():
                    if value is None:
                        stats[key] = 0
                self.ui.transparency_panel.update_stats(stats)
            
            recent_logs = self.db.get_recent_api_logs(20)
            for log in recent_logs:
                self.ui.transparency_panel.add_api_log({
                    "provider_name": log.provider_name,
                    "model_name": log.model_name,
                    "status_code": log.status_code,
                    "latency_ms": log.latency_ms,
                    "ttft_ms": log.ttft_ms,
                    "tokens_in": log.tokens_in,
                    "tokens_out": log.tokens_out,
                    "cost": log.cost,
                    "error": log.error
                })
        
        status_left = f"Session: {self.current_session.name if self.current_session else 'None'}"
        status_center = f"Agent: {self.current_agent.name if self.current_agent else 'Default'}"
        status_right = "[?] Help"
        
        self.ui.status_bar.render(status_left, status_center, status_right)
        self.ui.render()
    
    def _handle_command(self):
        """Handle command input."""
        self.ui.input_panel.input_text = "/"
        command = self.ui.input_panel.get_input("/")
        
        if not command:
            return
        
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/help" or cmd == "/?":
            self._show_help()
        elif cmd == "/clear":
            self._clear_chat()
        elif cmd == "/session" or cmd == "/s":
            self._switch_session()
        elif cmd == "/new" or cmd == "/n":
            self._create_new_session()
        elif cmd == "/agent" or cmd == "/a":
            self._select_agent()
        elif cmd == "/model" or cmd == "/m":
            self._select_model()
        elif cmd == "/provider" or cmd == "/p":
            self._manage_providers()
        elif cmd == "/agents" or cmd == "/g":
            self._manage_agents()
        elif cmd == "/tools" or cmd == "/t":
            self._manage_tools()
        elif cmd == "/quit" or cmd == "/q":
            sys.exit(0)
        elif cmd == "/stats":
            self._show_stats()
        elif cmd == "/providers":
            self._list_providers()
        elif cmd == "/models":
            self._list_models()
        elif cmd == "/agents":
            self._list_agents()
        else:
            self.ui.show_message(f"Unknown command: {cmd}\nUse /help for available commands.")
    
    def _handle_user_input(self):
        """Handle user message input."""
        if not self.current_session:
            self.ui.show_message("No active session. Create or select a session first.")
            return
        
        input_text = self.ui.input_panel.input_text
        if not input_text.strip():
            return
        
        self.ui.input_panel.clear_input()
        
        system_prompt = ""
        if self.current_agent:
            system_prompt = self.current_agent.system_prompt
        
        provider_name = self.current_agent.provider_name if self.current_agent else self.config.default_provider
        model_name = self.current_agent.model_name if self.current_agent else self.config.default_model
        
        if not model_name:
            models = self.db.get_models(provider_name)
            if models:
                model_name = models[0].model_id
            else:
                self.ui.show_message(f"No models available for provider: {provider_name}")
                return
        
        self._send_message(input_text, provider_name, model_name, system_prompt)
    
    def _send_message(self, content: str, provider_name: str, model_name: str, system_prompt: str = ""):
        """Send message to AI provider."""
        provider = self.providers.get(provider_name)
        if not provider:
            self.ui.show_message(f"Provider not available: {provider_name}")
            return
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        history = self.db.get_messages(self.current_session.id)
        for msg in history[-50:]:
            messages.append({"role": msg.role, "content": msg.content})
        
        messages.append({"role": "user", "content": content})
        
        self.ui.chat_panel.add_message("user", content)
        self.ui.render()
        
        import time
        start_time = time.time()
        
        try:
            model = self.db.get_model(provider_name, model_name)
            
            response, usage = provider.chat(messages, model_name if model else None)
            
            ttft = (time.time() - start_time) * 1000
            
            tokens_in = usage.get("tokens_in", 0) if usage else 0
            tokens_out = usage.get("tokens_out", 0) if usage else 0
            latency_ms = (time.time() - start_time) * 1000
            
            cost = 0.0
            if model and tokens_in and tokens_out:
                cost = (tokens_in * model.cost_per_input / 1000) + (tokens_out * model.cost_per_output / 1000)
            
            tokens_per_second = (tokens_out / latency_ms * 1000) if tokens_out and latency_ms > 0 else 0
            
            user_msg = Message(
                id=str(uuid.uuid4()),
                session_id=self.current_session.id,
                role="user",
                content=content,
                tool_calls=None,
                tool_results=None,
                tokens_in=tokens_in,
                tokens_out=0,
                latency_ms=0,
                ttft_ms=0,
                cost=0,
                created_at=datetime.now().isoformat()
            )
            self.db.create_message(user_msg)
            
            assistant_msg = Message(
                id=str(uuid.uuid4()),
                session_id=self.current_session.id,
                role="assistant",
                content=response,
                tool_calls=None,
                tool_results=None,
                tokens_in=0,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                ttft_ms=ttft,
                cost=cost,
                created_at=datetime.now().isoformat()
            )
            self.db.create_message(assistant_msg)
            
            api_log = APILog(
                id=str(uuid.uuid4()),
                session_id=self.current_session.id,
                provider_name=provider_name,
                model_name=model_name,
                request_type="chat",
                request_data=json.dumps({"messages": len(messages), "model": model_name}),
                response_data=None,
                status_code=200,
                error=None,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                ttft_ms=ttft,
                cost=cost,
                created_at=datetime.now().isoformat()
            )
            self.db.create_api_log(api_log)
            
            self.ui.chat_panel.add_message("assistant", response, {
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": latency_ms,
                "ttft_ms": ttft,
                "cost": cost,
                "tokens_per_second": tokens_per_second
            })
            
            self._update_session()
            
        except Exception as e:
            error_msg = str(e)
            
            api_log = APILog(
                id=str(uuid.uuid4()),
                session_id=self.current_session.id,
                provider_name=provider_name,
                model_name=model_name,
                request_type="chat",
                request_data=json.dumps({"messages": len(messages), "model": model_name}),
                response_data=None,
                status_code=500,
                error=error_msg,
                tokens_in=0,
                tokens_out=0,
                latency_ms=(time.time() - start_time) * 1000,
                ttft_ms=0,
                cost=0,
                created_at=datetime.now().isoformat()
            )
            self.db.create_api_log(api_log)
            
            self.ui.show_message(f"Error: {error_msg}")
    
    def _update_session(self):
        """Update session timestamp."""
        if self.current_session:
            self.db.update_session(self.current_session)
    
    def _clear_chat(self):
        """Clear chat history."""
        if self.current_session:
            with self.db.get_connection() as conn:
                conn.execute("DELETE FROM messages WHERE session_id = ?", (self.current_session.id,))
                conn.commit()
            self.ui.chat_panel.clear_chat()
    
    def _create_new_session(self):
        """Create a new chat session."""
        name = self.ui.input_panel.get_input("Session name: ")
        if not name:
            name = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        agent = self.current_agent
        provider = agent.provider_name if agent else self.config.default_provider
        model = agent.model_name if agent else self.config.default_model
        
        if not model:
            models = self.db.get_models(provider)
            if models:
                model = models[0].model_id
        
        session = Session(
            id=str(uuid.uuid4()),
            name=name,
            agent_id=agent.id if agent else None,
            provider_name=provider,
            model_name=model,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        self.db.create_session(session)
        self.current_session = session
        self.ui.chat_panel.clear_chat()
    
    def _switch_session(self):
        """Switch to a different session."""
        sessions = self.db.get_sessions()
        if not sessions:
            self.ui.show_message("No sessions available.")
            return
        
        session_names = [s.name for s in sessions]
        
        def on_select(index, name):
            self.current_session = sessions[index]
        
        self.ui.show_menu(" Select Session ", session_names, on_select)
    
    def _select_agent(self):
        """Select an agent."""
        agents = self.db.get_agents()
        if not agents:
            self.ui.show_message("No agents available.")
            return
        
        agent_names = [a.name for a in agents]
        
        def on_select(index, name):
            self.current_agent = agents[index]
            self.ui.show_message(f"Selected agent: {name}")
        
        self.ui.show_menu(" Select Agent ", agent_names, on_select)
    
    def _select_model(self):
        """Select a model."""
        provider_name = self.current_agent.provider_name if self.current_agent else self.config.default_provider
        models = self.db.get_models(provider_name)
        
        if not models:
            self.ui.show_message("No models available.")
            return
        
        model_names = [m.name for m in models]
        
        def on_select(index, name):
            if self.current_agent:
                self.current_agent.model_name = models[index].model_id
                self.db.update_agent(self.current_agent)
            self.ui.show_message(f"Selected model: {name}")
        
        self.ui.show_menu(" Select Model ", model_names, on_select)
    
    def _manage_providers(self):
        """Manage providers."""
        providers = self.db.get_providers()
        provider_names = [p.name for p in providers]
        provider_names.extend(["[Add Provider]", "[Back]"])
        
        def on_select(index, name):
            if name == "[Add Provider]":
                self._add_provider()
            elif name == "[Back]":
                return
            elif index < len(providers):
                self._edit_provider(providers[index])
        
        self.ui.show_menu(" Manage Providers ", provider_names, on_select)
    
    def _add_provider(self):
        """Add a new provider."""
        fields = ["Name", "Type (openai/anthropic/ollama/local)", "API Key", "Base URL"]
        is_defaults = ["", "openai", "", ""]
        
        results = self.ui.show_form(" Add Provider ", fields, is_defaults)
        if not results:
            return
        
        provider = Provider(
            id=str(uuid.uuid4()),
            name=results[0],
            provider_type=results[1].lower(),
            api_key=results[2] or None,
            base_url=results[3] or None,
            enabled=True,
            extra="{}",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        try:
            self.db.create_provider(provider)
            self.ui.show_message("Provider added successfully!")
        except Exception as e:
            self.ui.show_message(f"Error adding provider: {e}")
    
    def _edit_provider(self, provider: Provider):
        """Edit an existing provider."""
        fields = ["Name", "Type", "API Key", "Base URL", "Enabled (1/0)"]
        is_defaults = [provider.name, provider.provider_type, 
                   provider.api_key or "", provider.base_url or "", 
                   str(int(provider.enabled))]
        
        results = self.ui.show_form(f" Edit Provider: {provider.name} ", fields, is_defaults)
        if not results:
            return
        
        provider.name = results[0]
        provider.provider_type = results[1]
        provider.api_key = results[2] or None
        provider.base_url = results[3] or None
        provider.enabled = results[4] == "1"
        provider.updated_at = datetime.now().isoformat()
        
        try:
            self.db.update_provider(provider)
            self.ui.show_message("Provider updated successfully!")
        except Exception as e:
            self.ui.show_message(f"Error updating provider: {e}")
    
    def _manage_agents(self):
        """Manage agents."""
        agents = self.db.get_agents()
        agent_names = [a.name for a in agents]
        agent_names.extend(["[Add Agent]", "[Back]"])
        
        def on_select(index, name):
            if name == "[Add Agent]":
                self._add_agent()
            elif name == "[Back]":
                return
            elif index < len(agents):
                self._edit_agent(agents[index])
        
        self.ui.show_menu(" Manage Agents ", agent_names, on_select)
    
    def _add_agent(self):
        """Add a new agent."""
        providers = self.db.get_providers(enabled_only=True)
        provider_names = [p.name for p in providers]
        
        if not provider_names:
            self.ui.show_message("No providers available.")
            return
        
        models = self.db.get_models(provider_names[0])
        model_names = [m.name for m in models]
        
        fields = ["Name", "System Prompt", "Provider", "Model"]
        is_defaults = ["", "You are a helpful AI assistant.", provider_names[0], model_names[0] if model_names else ""]
        
        results = self.ui.show_form(" Add Agent ", fields, is_defaults)
        if not results:
            return
        
        agent = Agent(
            id=str(uuid.uuid4()),
            name=results[0],
            system_prompt=results[1],
            provider_name=results[2],
            model_name=results[3],
            tools="[]",
            enabled=True,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        try:
            self.db.create_agent(agent)
            self.ui.show_message("Agent added successfully!")
        except Exception as e:
            self.ui.show_message(f"Error adding agent: {e}")
    
    def _edit_agent(self, agent: Agent):
        """Edit an existing agent."""
        fields = ["Name", "System Prompt", "Provider", "Model", "Enabled (1/0)"]
        is_defaults = [agent.name, agent.system_prompt, agent.provider_name, 
                   agent.model_name, str(int(agent.enabled))]
        
        results = self.ui.show_form(f" Edit Agent: {agent.name} ", fields, is_defaults)
        if not results:
            return
        
        agent.name = results[0]
        agent.system_prompt = results[1]
        agent.provider_name = results[2]
        agent.model_name = results[3]
        agent.enabled = results[4] == "1"
        agent.updated_at = datetime.now().isoformat()
        
        try:
            self.db.update_agent(agent)
            self.ui.show_message("Agent updated successfully!")
        except Exception as e:
            self.ui.show_message(f"Error updating agent: {e}")
    
    def _manage_tools(self):
        """Manage tools."""
        tools = self.db.get_tools()
        tool_names = [t.name for t in tools]
        tool_names.extend(["[Add Tool]", "[Back]"])
        
        def on_select(index, name):
            if name == "[Add Tool]":
                self._add_tool()
            elif name == "[Back]":
                return
            elif index < len(tools):
                self._edit_tool(tools[index])
        
        self.ui.show_menu(" Manage Tools ", tool_names, on_select)
    
    def _add_tool(self):
        """Add a new tool."""
        fields = ["Name", "Description", "Parameters (JSON)", "Function (Python code)"]
        is_defaults = ["", "", '{"type": "object", "properties": {}}', ""]
        
        results = self.ui.show_form(" Add Tool ", fields, is_defaults)
        if not results:
            return
        
        tool = Tool(
            id=str(uuid.uuid4()),
            name=results[0],
            description=results[1],
            parameters=results[2],
            function=results[3],
            enabled=True,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        try:
            self.db.create_tool(tool)
            self.ui.show_message("Tool added successfully!")
        except Exception as e:
            self.ui.show_message(f"Error adding tool: {e}")
    
    def _edit_tool(self, tool: Tool):
        """Edit an existing tool."""
        fields = ["Name", "Description", "Parameters", "Function", "Enabled (1/0)"]
        is_defaults = [tool.name, tool.description, tool.parameters, 
                   tool.function, str(int(tool.enabled))]
        
        results = self.ui.show_form(f" Edit Tool: {tool.name} ", fields, is_defaults)
        if not results:
            return
        
        tool.name = results[0]
        tool.description = results[1]
        tool.parameters = results[2]
        tool.function = results[3]
        tool.enabled = results[4] == "1"
        tool.updated_at = datetime.now().isoformat()
        
        try:
            self.db.update_tool(tool)
            self.ui.show_message("Tool updated successfully!")
        except Exception as e:
            self.ui.show_message(f"Error updating tool: {e}")
    
    def _show_help(self):
        """Show help message."""
        help_text = """
=== Terminal AI Chat - Help ===

Commands:
  /help, /?    Show this help message
  /clear       Clear chat history
  /session, /s Switch to a different session
  /new, /n     Create a new session
  /agent, /a   Select an agent
  /model, /m   Select a model
  /provider, /p Manage providers
  /agents, /g  Manage agents
  /tools, /t   Manage tools
  /stats       Show statistics
  /quit, /q    Exit the application

Keyboard shortcuts:
  c            Clear chat
  s            Switch session
  a            Select agent
  m            Select model
  p            Manage providers
  g            Manage agents
  t            Manage tools
  n            New session
  h or ?       Show help
  q            Quit

Tips:
  - Messages are saved in SQLite database
  - All API calls are logged in the transparency panel
  - Statistics are tracked per session and provider
  - Use agents to customize AI behavior
        """.strip()
        
        self.ui.show_message(help_text, " Help ")
    
    def _show_stats(self):
        """Show statistics."""
        stats = self.db.get_all_time_stats()
        
        stats_text = f"""
=== Statistics ===

Total Requests: {stats.get('total_requests', 0)}
Total Tokens In: {stats.get('total_tokens_in', 0)}
Total Tokens Out: {stats.get('total_tokens_out', 0)}
Total Cost: ${stats.get('total_cost', 0):.4f}
Avg Latency: {stats.get('avg_latency', 0):.0f}ms
Avg TTFT: {stats.get('avg_ttft', 0):.0f}ms
        """.strip()
        
        self.ui.show_message(stats_text, " Statistics ")
    
    def _list_providers(self):
        """List all providers."""
        providers = self.db.get_providers()
        
        if not providers:
            self.ui.show_message("No providers configured.")
            return
        
        provider_list = "\n".join([
            f"{p.name} ({p.provider_type}) - {'Enabled' if p.enabled else 'Disabled'}"
            for p in providers
        ])
        
        self.ui.show_message(provider_list, " Providers ")
    
    def _list_models(self):
        """List all models."""
        models = self.db.get_models()
        
        if not models:
            self.ui.show_message("No models configured.")
            return
        
        model_list = "\n".join([
            f"{m.name} ({m.provider_name}) - {m.model_id}"
            for m in models
        ])
        
        self.ui.show_message(model_list, " Models ")
    
    def _list_agents(self):
        """List all agents."""
        agents = self.db.get_agents()
        
        if not agents:
            self.ui.show_message("No agents configured.")
            return
        
        agent_list = "\n".join([
            f"{a.name} - {a.provider_name}/{a.model_name}"
            for a in agents
        ])
        
        self.ui.show_message(agent_list, " Agents ")
