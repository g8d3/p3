# Smart Contract Security Web App

This project provides a simple Flask web application that offers three main capabilities:

1. **Datasets** – Retrieve a list of smart‑contract‑related data sources.
2. **Audit** – Submit Solidity source code to the MythX analysis API (requires a MythX API key).
3. **Monitor** – Placeholder endpoint for future real‑time contract monitoring.

## Project Structure
```
smart‑contract‑security/
├─ app/
│   ├─ __init__.py      # Flask app factory
│   └─ routes.py        # Blueprint with the three endpoints
├─ run.py               # Entry‑point to start the development server
├─ requirements.txt     # Python dependencies
├─ .env                 # Environment variables (MythX API key)
└─ README.md            # This file
```

## Setup Instructions
1. **Clone the repository** (if you haven't already):
   ```bash
   git clone <repo‑url>
   cd smart‑contract‑security
   ```

2. **Create a virtual environment** (recommended to avoid polluting the system Python):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   *If you encounter a "externally‑managed environment" warning, ensure the `python3‑venv` package is installed on the host (requires root).*

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the MythX API key**:
   - Copy the provided `.env` file and replace `YOUR_API_KEY_HERE` with your actual MythX API key.
   - The app reads this variable via `python‑dotenv`.

5. **Run the development server**:
   ```bash
   python run.py
   ```
   The server will listen on `http://0.0.0.0:5000`.

## API Endpoints
- `GET /datasets`
  Returns a JSON payload with a couple of example data sources.

- `POST /audit`
  Expects a JSON body:
  ```json
  {"source": "<solidity source code>"}
  ```
  The endpoint forwards the source to MythX and returns the analysis JSON (or an error).

- `GET /monitor`
  Currently a placeholder that returns `{"status": "monitoring not implemented yet"}`.

## Extending the Application
- **Real‑time monitoring**: integrate websockets (e.g., Flask‑SocketIO) to push live alerts.
- **Dataset aggregation**: replace the static list with calls to services like Etherscan, OpenZeppelin, or other open‑source repositories.
- **Authentication**: add user auth to protect the audit endpoint and rate‑limit requests.

---
*This scaffold is intentionally minimal; you can expand it according to your security workflow.*