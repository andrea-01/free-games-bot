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

@pytest.mark.asyncio
async def test_unknown_message_handler():
    from unittest.mock import AsyncMock, MagicMock
    bot = FreeGamesBot()

    # Test unknown command
    update_cmd = MagicMock()
    update_cmd.effective_message.text = "/invalidcommand"
    update_cmd.effective_message.reply_text = AsyncMock()
    update_cmd.effective_user.username = "testuser"
    update_cmd.effective_chat.id = 12345

    await bot.unknown_message_handler(update_cmd, MagicMock())
    update_cmd.effective_message.reply_text.assert_called_once()
    called_text = update_cmd.effective_message.reply_text.call_args[0][0]
    assert "Comando non riconosciuto" in called_text

    # Test plain text message
    update_text = MagicMock()
    update_text.effective_message.text = "ciao bot"
    update_text.effective_message.reply_text = AsyncMock()
    update_text.effective_user.username = "testuser"
    update_text.effective_chat.id = 12345

    await bot.unknown_message_handler(update_text, MagicMock())
    update_text.effective_message.reply_text.assert_called_once()
    called_text2 = update_text.effective_message.reply_text.call_args[0][0]
    assert "Comando non riconosciuto" in called_text2

