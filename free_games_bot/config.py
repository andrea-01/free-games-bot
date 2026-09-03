"""Configuration settings for Free Games Bot."""
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load from .env in the project root if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass(frozen=True)
class Config:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    steamgriddb_api_key: str = os.getenv("STEAMGRIDDB_API_KEY", "").strip()
    check_interval_minutes: int = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
    database_path: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "free_games.db"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

config = Config()
