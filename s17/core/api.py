"""HTTP API server for terminal AI chat app."""

import json
import uuid
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional
from datetime import datetime
from core.database import Database, Provider, Model, Agent, Session, Message, APILog


class APIHandler(BaseHTTPRequestHandler):
    """HTTP API request handler."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def send_json(self, status: int, data: Dict):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def get_json(self) -> Dict:
        """Read JSON from request body."""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            return json.loads(self.rfile.read(content_length))
        return {}

    def get_db(self) -> Database:
        """Get database instance."""
        return self.server.db

    def get_app(self):
        """Get app instance."""
        return self.server.app

    def do_GET(self):
        """Handle GET requests."""
        path = urlparse(self.path).path

        if path == '/health':
            self.handle_health()
        elif path == '/providers':
            self.handle_list_providers()
        elif path == '/models':
            self.handle_list_models()
        elif path == '/agents':
            self.handle_list_agents()
        elif path == '/sessions':
            self.handle_list_sessions()
        elif path.startswith('/sessions/'):
            self.handle_get_session(path)
        elif path == '/stats':
            self.handle_stats()
        elif path == '/api-logs':
            self.handle_api_logs()
        elif path == '/screen':
            self.handle_get_screen()
        elif path == '/state':
            self.handle_get_state()
        else:
            self.send_json(404, {'error': 'Not found'})

    def do_POST(self):
        """Handle POST requests."""
        path = urlparse(self.path).path
        data = self.get_json()

        if path == '/providers':
            self.handle_create_provider(data)
        elif path == '/models':
            self.handle_create_model(data)
        elif path == '/agents':
            self.handle_create_agent(data)
        elif path == '/sessions':
            self.handle_create_session(data)
        elif path == '/chat':
            self.handle_chat(data)
        elif path == '/keystroke':
            self.handle_keystroke(data)
        elif path == '/keystrokes':
            self.handle_keystrokes(data)
        elif path == '/run-schedule':
            self.handle_run_schedule(data)
        else:
            self.send_json(404, {'error': 'Not found'})

    def do_PUT(self):
        """Handle PUT requests."""
        path = urlparse(self.path).path
        data = self.get_json()

        if path.startswith('/providers/'):
            self.handle_update_provider(path, data)
        elif path.startswith('/models/'):
            self.handle_update_model(path, data)
        elif path.startswith('/agents/'):
            self.handle_update_agent(path, data)
        elif path.startswith('/sessions/'):
            self.handle_update_session(path, data)
        else:
            self.send_json(404, {'error': 'Not found'})

    def do_DELETE(self):
        """Handle DELETE requests."""
        path = urlparse(self.path).path

        if path.startswith('/providers/'):
            self.handle_delete_provider(path)
        elif path.startswith('/models/'):
            self.handle_delete_model(path)
        elif path.startswith('/agents/'):
            self.handle_delete_agent(path)
        elif path.startswith('/sessions/'):
            self.handle_delete_session(path)
        else:
            self.send_json(404, {'error': 'Not found'})

    def handle_health(self):
        """Health check endpoint."""
        self.send_json(200, {'status': 'healthy', 'timestamp': datetime.now().isoformat()})

    def handle_list_providers(self):
        """List all providers."""
        providers = self.get_db().get_providers()
        self.send_json(200, {'providers': [p.to_dict() for p in providers]})

    def handle_create_provider(self, data: Dict):
        """Create a new provider."""
        provider = Provider(
            id=str(uuid.uuid4()),
            name=data['name'],
            provider_type=data['provider_type'],
            api_key=data.get('api_key'),
            base_url=data.get('base_url'),
            enabled=data.get('enabled', True),
            extra=json.dumps(data.get('extra', {})),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        self.get_db().create_provider(provider)
        self.send_json(201, provider.to_dict())

    def handle_update_provider(self, path: str, data: Dict):
        """Update a provider."""
        name = path.split('/')[-1]
        db_provider = self.get_db().get_provider(name)
        if not db_provider:
            self.send_json(404, {'error': 'Provider not found'})
            return

        db_provider.name = data.get('name', db_provider.name)
        db_provider.provider_type = data.get('provider_type', db_provider.provider_type)
        db_provider.api_key = data.get('api_key', db_provider.api_key)
        db_provider.base_url = data.get('base_url', db_provider.base_url)
        db_provider.enabled = data.get('enabled', db_provider.enabled)
        db_provider.extra = json.dumps(data.get('extra', json.loads(db_provider.extra)))
        db_provider.updated_at = datetime.now().isoformat()

        self.get_db().update_provider(db_provider)
        self.send_json(200, db_provider.to_dict())

    def handle_delete_provider(self, path: str):
        """Delete a provider."""
        name = path.split('/')[-1]
        self.get_db().delete_provider(name)
        self.send_json(200, {'message': 'Provider deleted'})

    def handle_list_models(self):
        """List all models."""
        models = self.get_db().get_models()
        self.send_json(200, {'models': [m.to_dict() for m in models]})

    def handle_create_model(self, data: Dict):
        """Create a new model."""
        model = Model(
            id=str(uuid.uuid4()),
            name=data['name'],
            provider_name=data['provider_name'],
            model_id=data['model_id'],
            context_window=data.get('context_window', 128000),
            max_tokens=data.get('max_tokens', 4096),
            cost_per_input=data.get('cost_per_input', 0.0),
            cost_per_output=data.get('cost_per_output', 0.0),
            is_default=data.get('is_default', False),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        self.get_db().create_model(model)
        self.send_json(201, model.to_dict())

    def handle_update_model(self, path: str, data: Dict):
        """Update a model."""
        model_id = path.split('/')[-1]
        db_models = self.get_db().get_models()
        db_model = next((m for m in db_models if m.id == model_id), None)
        if not db_model:
            self.send_json(404, {'error': 'Model not found'})
            return

        db_model.name = data.get('name', db_model.name)
        db_model.provider_name = data.get('provider_name', db_model.provider_name)
        db_model.model_id = data.get('model_id', db_model.model_id)
        db_model.context_window = data.get('context_window', db_model.context_window)
        db_model.max_tokens = data.get('max_tokens', db_model.max_tokens)
        db_model.cost_per_input = data.get('cost_per_input', db_model.cost_per_input)
        db_model.cost_per_output = data.get('cost_per_output', db_model.cost_per_output)
        db_model.is_default = data.get('is_default', db_model.is_default)
        db_model.updated_at = datetime.now().isoformat()

        self.get_db().update_model(db_model)
        self.send_json(200, db_model.to_dict())

    def handle_delete_model(self, path: str):
        """Delete a model."""
        model_id = path.split('/')[-1]
        self.get_db().delete_model(model_id)
        self.send_json(200, {'message': 'Model deleted'})

    def handle_list_agents(self):
        """List all agents."""
        agents = self.get_db().get_agents()
        self.send_json(200, {'agents': [a.to_dict() for a in agents]})

    def handle_create_agent(self, data: Dict):
        """Create a new agent."""
        agent = Agent(
            id=str(uuid.uuid4()),
            name=data['name'],
            system_prompt=data['system_prompt'],
            provider_name=data['provider_name'],
            model_name=data['model_name'],
            tools=json.dumps(data.get('tools', [])),
            enabled=data.get('enabled', True),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        self.get_db().create_agent(agent)
        self.send_json(201, agent.to_dict())

    def handle_update_agent(self, path: str, data: Dict):
        """Update an agent."""
        agent_id = path.split('/')[-1]
        db_agents = self.get_db().get_agents()
        db_agent = next((a for a in db_agents if a.id == agent_id), None)
        if not db_agent:
            self.send_json(404, {'error': 'Agent not found'})
            return

        db_agent.name = data.get('name', db_agent.name)
        db_agent.system_prompt = data.get('system_prompt', db_agent.system_prompt)
        db_agent.provider_name = data.get('provider_name', db_agent.provider_name)
        db_agent.model_name = data.get('model_name', db_agent.model_name)
        db_agent.tools = json.dumps(data.get('tools', json.loads(db_agent.tools)))
        db_agent.enabled = data.get('enabled', db_agent.enabled)
        db_agent.updated_at = datetime.now().isoformat()

        self.get_db().update_agent(db_agent)
        self.send_json(200, db_agent.to_dict())

    def handle_delete_agent(self, path: str):
        """Delete an agent."""
        agent_id = path.split('/')[-1]
        self.get_db().delete_agent(agent_id)
        self.send_json(200, {'message': 'Agent deleted'})

    def handle_list_sessions(self):
        """List all sessions."""
        sessions = self.get_db().get_sessions()
        self.send_json(200, {'sessions': [s.to_dict() for s in sessions]})

    def handle_get_session(self, path: str):
        """Get a specific session with messages."""
        session_id = path.split('/')[-1]
        session = self.get_db().get_session(session_id)
        if not session:
            self.send_json(404, {'error': 'Session not found'})
            return

        messages = self.get_db().get_messages(session_id)
        self.send_json(200, {
            'session': session.to_dict(),
            'messages': [m.to_dict() for m in messages]
        })

    def handle_create_session(self, data: Dict):
        """Create a new session."""
        session = Session(
            id=str(uuid.uuid4()),
            name=data['name'],
            agent_id=data.get('agent_id'),
            provider_name=data['provider_name'],
            model_name=data['model_name'],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        self.get_db().create_session(session)
        self.send_json(201, session.to_dict())

    def handle_update_session(self, path: str, data: Dict):
        """Update a session."""
        session_id = path.split('/')[-1]
        db_session = self.get_db().get_session(session_id)
        if not db_session:
            self.send_json(404, {'error': 'Session not found'})
            return

        db_session.name = data.get('name', db_session.name)
        db_session.agent_id = data.get('agent_id', db_session.agent_id)
        db_session.provider_name = data.get('provider_name', db_session.provider_name)
        db_session.model_name = data.get('model_name', db_session.model_name)
        db_session.updated_at = datetime.now().isoformat()

        self.get_db().update_session(db_session)
        self.send_json(200, db_session.to_dict())

    def handle_delete_session(self, path: str):
        """Delete a session."""
        session_id = path.split('/')[-1]
        self.get_db().delete_session(session_id)
        self.send_json(200, {'message': 'Session deleted'})

    def handle_chat(self, data: Dict):
        """Send a chat message and get response."""
        session_id = data.get('session_id')
        message = data.get('message')

        if not session_id or not message:
            self.send_json(400, {'error': 'session_id and message required'})
            return

        session = self.get_db().get_session(session_id)
        if not session:
            self.send_json(404, {'error': 'Session not found'})
            return

        start_time = datetime.now()

        user_message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role='user',
            content=message,
            tool_calls=None,
            tool_results=None,
            tokens_in=0,
            tokens_out=0,
            latency_ms=0,
            ttft_ms=0,
            cost=0,
            created_at=datetime.now().isoformat()
        )
        self.get_db().create_message(user_message)

        response_content = f"[API Mode] Received: {message}\n\nSession: {session.name}\nProvider: {session.provider_name}\nModel: {session.model_name}"
        tokens_out = len(response_content) // 4

        latency_ms = (datetime.now() - start_time).total_seconds() * 1000

        assistant_message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role='assistant',
            content=response_content,
            tool_calls=None,
            tool_results=None,
            tokens_in=len(message) // 4,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            ttft_ms=latency_ms * 0.1,
            cost=0,
            created_at=datetime.now().isoformat()
        )
        self.get_db().create_message(assistant_message)

        self.send_json(200, {
            'response': response_content,
            'message_id': assistant_message.id,
            'latency_ms': latency_ms,
            'tokens_out': tokens_out
        })

    def handle_stats(self):
        """Get performance statistics."""
        stats = self.get_db().get_all_time_stats()
        providers = self.get_db().get_providers()
        provider_stats = {}

        for provider in providers:
            provider_stats[provider.name] = self.get_db().get_provider_stats(provider.name)

        self.send_json(200, {
            'all_time': stats,
            'by_provider': provider_stats
        })

    def handle_api_logs(self):
        """Get recent API logs."""
        logs = self.get_db().get_recent_api_logs(50)
        self.send_json(200, {'api_logs': [log.to_dict() for log in logs]})

    def handle_keystroke(self, data: Dict):
        """Send a keystroke to the TUI."""
        key = data.get('key')
        if not key:
            self.send_json(400, {'error': 'key required'})
            return

        app = self.get_app()
        if not app or not hasattr(app, 'ui') or not app.ui:
            self.send_json(503, {'error': 'TUI not running'})
            return

        success = app.ui.inject_key(key)
        self.send_json(200, {
            'success': success,
            'key': key,
            'timestamp': datetime.now().isoformat()
        })

    def handle_keystrokes(self, data: Dict):
        """Send multiple keystrokes to the TUI."""
        keys = data.get('keys', [])
        delay = data.get('delay', 0.1)

        if not keys:
            self.send_json(400, {'error': 'keys required'})
            return

        app = self.get_app()
        if not app or not hasattr(app, 'ui') or not app.ui:
            self.send_json(503, {'error': 'TUI not running'})
            return

        results = []
        for key in keys:
            success = app.ui.inject_key(key)
            results.append({'key': key, 'success': success})
            time.sleep(delay)

        self.send_json(200, {
            'results': results,
            'timestamp': datetime.now().isoformat()
        })

    def handle_get_screen(self):
        """Get current screen contents."""
        app = self.get_app()
        if not app or not hasattr(app, 'ui') or not app.ui:
            self.send_json(503, {'error': 'TUI not running'})
            return

        screen_text = app.ui.get_screen_text()
        self.send_json(200, {
            'screen': screen_text,
            'timestamp': datetime.now().isoformat()
        })

    def handle_get_state(self):
        """Get current TUI state."""
        app = self.get_app()
        if not app or not hasattr(app, 'ui') or not app.ui:
            self.send_json(503, {'error': 'TUI not running'})
            return

        state = app.ui.get_state()
        self.send_json(200, {
            'state': state,
            'timestamp': datetime.now().isoformat()
        })

    def handle_run_schedule(self, data: Dict):
        """Run a scheduled task manually."""
        schedule_id = data.get('schedule_id')
        if not schedule_id:
            self.send_json(400, {'error': 'schedule_id required'})
            return

        schedules = self.get_db().get_schedules()
        schedule = next((s for s in schedules if s.id == schedule_id), None)
        if not schedule:
            self.send_json(404, {'error': 'Schedule not found'})
            return

        self.send_json(200, {
            'message': f"Schedule '{schedule.name}' would run with prompt: {schedule.prompt}",
            'schedule': schedule.to_dict()
        })


class APIServer(HTTPServer):
    """HTTP API server with database and app reference."""

    def __init__(self, host: str, port: int, db: Database, app=None):
        super().__init__((host, port), APIHandler)
        self.db = db
        self.app = app


def run_server(host: str = '0.0.0.0', port: int = 8080, db: Database = None, app=None):
    """Run the API server."""
    server = APIServer(host, port, db, app)
    print(f"API Server running on http://{host}:{port}")
    print()
    print("Data Endpoints:")
    print("  GET  /health              - Health check")
    print("  GET  /providers           - List providers")
    print("  POST /providers           - Create provider")
    print("  GET  /models              - List models")
    print("  POST /models              - Create model")
    print("  GET  /agents              - List agents")
    print("  POST /agents              - Create agent")
    print("  GET  /sessions            - List sessions")
    print("  POST /sessions            - Create session")
    print("  POST /chat                - Send chat message (data mode)")
    print("  GET  /stats               - Performance stats")
    print("  GET  /api-logs            - Recent API logs")
    print()
    print("TUI Control Endpoints (for AI agent testing):")
    print("  POST /keystroke           - Send single keystroke to TUI")
    print("  POST /keystrokes          - Send multiple keystrokes to TUI")
    print("  GET  /screen              - Get current TUI screen text")
    print("  GET  /state               - Get current TUI state")
    print()
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


def run_background_server(host: str = '0.0.0.0', port: int = 8080, db: Database = None, app=None):
    """Run the API server in a background thread."""
    server = APIServer(host, port, db, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
