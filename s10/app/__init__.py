"""Flask application factory for Smart Contract Security Web App.

Provides routes to gather datasets, perform contract audits via MythX, and monitor contracts in real-time.
"""

import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()  # Load .env variables

def create_app():
    app = Flask(__name__)
    # Config can be extended here
    from . import routes
    app.register_blueprint(routes.bp)
    return app
