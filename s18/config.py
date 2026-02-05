# Configuration

import os
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent
AGENTS_DIR = ROOT_DIR / "agents"
MEMORY_DIR = ROOT_DIR / "memory"
CREATIONS_DIR = ROOT_DIR / "creations"
LOG_DIR = ROOT_DIR / "logs"
STATE_FILE = ROOT_DIR / "state.json"
LOG_FILE = LOG_DIR / "bootstrap.log"
COMMANDS_FILE = ROOT_DIR / ".commands.json"
HUMAN_INPUT_FILE = MEMORY_DIR / "human_input.md"
AI_RESPONSES_FILE = MEMORY_DIR / "ai_responses.md"

# API Configuration
API_KEY = os.environ.get("GLM_API_KEY")
MODEL = "glm-4.7"
BASE_URL = "https://api.z.ai/api/coding/paas/v4"

# Default Settings
DEFAULT_INTERVALS = [1, 3, 5]
DEFAULT_VIEWPORT = "1920 1080"
MAX_LOG_LINES = 1000
MAX_TASK_HISTORY = 50
MAX_STATE_HISTORY = 5

# Browser Settings
BROWSER_PORT = 9222
HEADLESS_DEFAULT = True

# Logging Settings
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"
