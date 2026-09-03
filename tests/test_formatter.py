"""Unit tests for Telegram message formatting and keyboard generation."""
from free_games_bot.models import GameDeal
from free_games_bot.formatter import (
    format_deal_message,
    format_settings_message,
    build_settings_keyboard,
    MAX_CAPTION_LENGTH,
)
from free_games_bot.database import ALL_STORES

def test_format_active_deal():
    deal = GameDeal(
        id="deal_123",
        title="Portal 2",
        store="Steam",
        stock_price="$9.99",
        store_url="https://store.steampowered.com/app/620",
        release_year="2011",
        genres=["Action", "Puzzle"],
        player_modes=["Single-player", "Co-op"],
        end_date="2026-10-01 18:00 UTC",
        description="Portal 2 draws from the award-winning formula of innovative gameplay.",
    )

    caption, keyboard = format_deal_message(deal)

    assert "FREE GAME ALERT" in caption
    assert "<b>Portal 2</b>" in caption
    assert "<s>$9.99</s>" in caption
    assert "FREE (100% OFF)" in caption
    assert "2011" in caption
    assert "Action, Puzzle" in caption
    assert "Single-player, Co-op" in caption
    assert "2026-10-01 18:00 UTC" in caption

    assert keyboard is not None
    assert len(keyboard.inline_keyboard) == 1
    button = keyboard.inline_keyboard[0][0]
    assert button.text == "🎮 Claim on Steam"
    assert button.url == "https://store.steampowered.com/app/620"

def test_format_upcoming_deal():
    deal = GameDeal(
        id="deal_upcoming",
        title="Upcoming Masterpiece",
        store="Epic Games",
        stock_price="$29.99",
        store_url="https://store.epicgames.com",
        is_upcoming=True,
        end_date="Starts: 2026-09-10",
    )

    caption, keyboard = format_deal_message(deal)
    assert "[UPCOMING FREE GAME]" in caption
    assert "Upcoming Masterpiece" in caption
    assert "Will be 100% OFF" in caption
    button = keyboard.inline_keyboard[0][0]
    assert "View on Epic Games" in button.text

def test_caption_length_boundary():
    deal = GameDeal(
        id="long_deal",
        title="A" * 100,
        store="Epic Games",
        stock_price="$19.99",
        store_url="https://example.com",
        description="Very long text " * 150,
    )
    caption, _ = format_deal_message(deal)
    assert len(caption) <= MAX_CAPTION_LENGTH

def test_settings_formatting():
    enabled = {"Epic Games", "Steam"}
    msg = format_settings_message(enabled)
    assert "2 / 7 stores enabled" in msg

    keyboard = build_settings_keyboard(enabled)
    # Check that Epic Games has ✅ and GOG has ❌
    buttons_flat = [btn for row in keyboard.inline_keyboard for btn in row]
    epic_btn = next(b for b in buttons_flat if "Epic Games" in b.text)
    gog_btn = next(b for b in buttons_flat if "GOG" in b.text)

    assert "✅" in epic_btn.text
    assert "❌" in gog_btn.text
