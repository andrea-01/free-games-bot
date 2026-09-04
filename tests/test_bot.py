"""Test Telegram bot initialization and handlers registration."""
import pytest
from unittest.mock import patch
from free_games_bot.bot import FreeGamesBot
from free_games_bot.config import config

def test_build_application_handlers():
    """Ensure all command and message handlers are valid and build_application succeeds."""
    bot = FreeGamesBot()
    fake_config = type("FakeConfig", (), {"telegram_bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567", "check_interval_minutes": 60})()
    with patch("free_games_bot.bot.config", fake_config):
        app = bot.build_application()
        assert app is not None
        assert len(app.handlers.get(0, [])) > 0
