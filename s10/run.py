"""Entry point to run the Flask app for Smart Contract Security Web App.

Run with:
    python run.py
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    # Enable debugging for development
    app.run(host='0.0.0.0', port=5000, debug=True)
