#!/usr/bin/env python3
"""Terminal AI Chat Application - Main Entry Point"""

import sys
import os
import argparse
import threading
import traceback
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.app import TerminalAIApp
from core.api import run_server
from core.config import AppConfig

_app_instance = None


def signal_handler(signum, frame):
    """Handle signals for clean shutdown."""
    print("\nReceived signal, shutting down...")
    if _app_instance and hasattr(_app_instance, 'ui') and _app_instance.ui:
        try:
            _app_instance.ui.cleanup()
        except:
            pass
    sys.exit(0)


def run_tui(app):
    """Run the TUI in a separate thread."""
    global _app_instance
    _app_instance = app
    try:
        app.run()
    except Exception as e:
        print(f"TUI Error: {e}")
        traceback.print_exc()
    finally:
        if hasattr(app, 'ui') and app.ui:
            try:
                app.ui.cleanup()
            except:
                pass


def main():
    global _app_instance

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description='Terminal AI Chat Application')
    parser.add_argument('--api', action='store_true', help='Run in API server mode')
    parser.add_argument('--host', default='0.0.0.0', help='API server host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080, help='API server port (default: 8080)')
    args = parser.parse_args()

    if args.api:
        app = TerminalAIApp()
        _app_instance = app
        print("Starting Terminal AI Chat App with API Server...")
        print(f"Database: {app.config.database_path}")
        print(f"Providers: {len(app.db.get_providers())}")
        print(f"Models: {len(app.db.get_models())}")
        print(f"Agents: {len(app.db.get_agents())}")
        print()

        tui_thread = threading.Thread(target=run_tui, args=(app,), daemon=True)
        tui_thread.start()

        print("TUI thread started. Starting API server...")
        print("API Server running on http://0.0.0.0:8080")
        print()
        print("TUI Control Endpoints:")
        print("  POST /keystroke  - Send keystroke to TUI")
        print("  GET  /screen     - Get TUI screen text")
        print("  GET  /state      - Get TUI state")
        print()
        print("Press Ctrl+C to stop")
        print()

        run_server(host=args.host, port=args.port, db=app.db, app=app)
    else:
        app = TerminalAIApp()
        _app_instance = app
        try:
            app.run()
        except KeyboardInterrupt:
            print("\nExiting...")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
        finally:
            if hasattr(app, 'ui') and app.ui:
                try:
                    app.ui.cleanup()
                except:
                    pass


if __name__ == "__main__":
    main()
