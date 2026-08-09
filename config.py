"""
Central configuration for TaskMaster AI Bot.
All values are pulled from environment variables so the bot can be
deployed on Render / Railway / a VPS without touching code.
"""
import os
from pathlib import Path

# --- Core ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

# --- Storage ---
BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = Path(os.getenv("TEMP_DIR", BASE_DIR / "tmp_files"))
TEMP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "taskmaster.db"))

# --- File limits ---
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))  # Telegram bot API cap is 20MB for downloads
FILE_RETENTION_MINUTES = int(os.getenv("FILE_RETENTION_MINUTES", "30"))  # auto-delete temp files after this

# --- Rate limiting ---
RATE_LIMIT_COUNT = int(os.getenv("RATE_LIMIT_COUNT", "10"))     # max actions
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))   # per N seconds

# --- Task queue ---
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "3"))
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "50"))

# --- Translation ---
DEFAULT_TARGET_LANG = os.getenv("DEFAULT_TARGET_LANG", "en")

# --- Misc ---
BOT_NAME = "TaskMaster AI Bot"
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "")
