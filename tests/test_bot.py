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

@pytest.mark.asyncio
async def test_recap_command(tmp_path):
    from unittest.mock import AsyncMock, MagicMock
    from free_games_bot.database import Database
    from free_games_bot.fetchers.manager import DealManager
    from free_games_bot.models import GameDeal

    db = Database(db_path=str(tmp_path / "test_recap.db"))
    await db.init_db()

    deal_mgr = DealManager()
    sample_deal = GameDeal(
        id="test-deal-1",
        title="Test Game 1",
        store="Epic Games",
        stock_price="19,99 €",
        sale_price_value=0.0,
        store_url="https://store.epicgames.com/test",
        rating_percent=85,
        reviews_count=1000,
        genres=["Action"],
    )
    deal_mgr.fetch_all_deals = AsyncMock(return_value=[sample_deal])

    bot = FreeGamesBot(db=db, deal_manager=deal_mgr)

    update = MagicMock()
    update.effective_chat.id = 99999
    update.effective_user.username = "gamer"
    status_msg = MagicMock()
    status_msg.delete = AsyncMock()
    update.effective_message.reply_text = AsyncMock(side_effect=[status_msg, None])

    context = MagicMock()

    await bot.recap_command(update, context)

    # Should have sent status message and then recap chunk
    assert update.effective_message.reply_text.call_count == 2
    sent_recap = update.effective_message.reply_text.call_args[0][0]
    assert "RECAP SERALE OFFERTE" in sent_recap
    assert "Test Game 1" in sent_recap
    assert "Riscatta su Epic Games" in sent_recap

@pytest.mark.asyncio
async def test_settings_toggle_sub_callback(tmp_path):
    from unittest.mock import AsyncMock, MagicMock
    from free_games_bot.database import Database

    db = Database(db_path=str(tmp_path / "test_cb.db"))
    await db.init_db()

    bot = FreeGamesBot(db=db)

    # Chat not yet subscribed
    chat_id = 77777
    update = MagicMock()
    query = MagicMock()
    query.message.chat.id = chat_id
    query.from_user.username = "gamer77"
    query.data = "toggle_sub"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update.callback_query = query

    # Press toggle_sub -> should become subscribed
    await bot.settings_callback(update, MagicMock())
    assert await db.is_subscribed(chat_id) is True
    query.edit_message_text.assert_called_once()
    msg_text = query.edit_message_text.call_args[1]["text"]
    assert "🔔 <b>ATTIVE</b>" in msg_text

    # Press toggle_sub again -> should become unsubscribed
    query.edit_message_text.reset_mock()
    await bot.settings_callback(update, MagicMock())
    assert await db.is_subscribed(chat_id) is False
    query.edit_message_text.assert_called_once()
    msg_text2 = query.edit_message_text.call_args[1]["text"]
    assert "🔕 <b>DISATTIVATE</b>" in msg_text2

@pytest.mark.asyncio
async def test_nofilter_recap_command(tmp_path):
    from unittest.mock import AsyncMock, MagicMock
    from free_games_bot.database import Database
    from free_games_bot.fetchers.manager import DealManager
    from free_games_bot.models import GameDeal

    db = Database(db_path=str(tmp_path / "test_nofilter_recap.db"))
    await db.init_db()

    deal_mgr = DealManager()
    sample_deal = GameDeal(
        id="test-deal-nofilter",
        title="Super Indie Adventures",
        store="Steam",
        stock_price="14,99 €",
        sale_price_value=0.0,
        store_url="https://store.steampowered.com/test",
        rating_percent=88,
        reviews_count=2500,
        genres=["Indie"],
    )
    deal_mgr.fetch_all_deals = AsyncMock(return_value=[sample_deal])

    bot = FreeGamesBot(db=db, deal_manager=deal_mgr)

    update = MagicMock()
    update.effective_chat.id = 88888
    update.effective_user.username = "nofilter_user"
    status_msg = MagicMock()
    status_msg.delete = AsyncMock()
    update.effective_message.reply_text = AsyncMock(side_effect=[status_msg, None])

    context = MagicMock()

    await bot.nofilter_recap_command(update, context)

    assert update.effective_message.reply_text.call_count == 2
    sent_recap = update.effective_message.reply_text.call_args[0][0]
    assert "RECAP OFFERTE PC (SENZA FILTRI)" in sent_recap
    assert "Super Indie Adventures" in sent_recap
    assert "Riscatta su Steam" in sent_recap

