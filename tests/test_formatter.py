"""Unit tests for Telegram message formatting and keyboard generation in Italian."""
from free_games_bot.models import GameDeal
from free_games_bot.formatter import (
    format_deal_message,
    format_main_settings_message,
    build_main_settings_keyboard,
    format_stores_settings_message,
    build_stores_keyboard,
    format_categories_settings_message,
    build_categories_keyboard,
    format_prices_settings_message,
    build_prices_keyboard,
    MAX_CAPTION_LENGTH,
)
from free_games_bot.database import ALL_STORES, ALL_CATEGORIES

def test_format_active_free_deal():
    deal = GameDeal(
        id="deal_123",
        title="Portal 2",
        store="Steam",
        stock_price="9,99 €",
        store_url="https://store.steampowered.com/app/620/?l=italian",
        release_year="2011",
        genres=["Azione", "Puzzle"],
        player_modes=["Giocatore singolo", "Co-op"],
        end_date="01 Ott 2026",
        description="Portal 2 porta avanti la formula innovativa del primo capitolo.",
    )

    caption, keyboard = format_deal_message(deal)

    assert "GIOCO GRATIS" in caption
    assert "<b>Portal 2</b>" in caption
    assert "<s>9,99 €</s>" in caption
    assert "GRATIS (100% di sconto)" in caption
    assert "2011" in caption
    assert "Azione, Puzzle" in caption
    assert "Giocatore singolo, Co-op" in caption
    assert "01 Ott 2026" in caption

    assert keyboard is not None
    assert len(keyboard.inline_keyboard) == 1
    button = keyboard.inline_keyboard[0][0]
    assert button.text == "🎮 Riscatta su Steam"
    assert button.url == "https://store.steampowered.com/app/620/?l=italian"

def test_format_discounted_deal():
    deal = GameDeal(
        id="deal_disc",
        title="The Witcher 3",
        store="Steam",
        stock_price="29,99 €",
        store_url="https://store.steampowered.com/app/292030/?l=italian",
        sale_price_value=4.49,
    )

    caption, keyboard = format_deal_message(deal)
    assert "OFFERTA PC" in caption
    assert "4,49 €" in caption
    button = keyboard.inline_keyboard[0][0]
    assert "Vedi Offerta su Steam" in button.text

def test_format_upcoming_deal():
    deal = GameDeal(
        id="deal_upcoming",
        title="Upcoming Masterpiece",
        store="Epic Games",
        stock_price="29,99 €",
        store_url="https://store.epicgames.com/it/p/upcoming",
        is_upcoming=True,
        end_date="Inizia: 10 Set 2026",
    )

    caption, keyboard = format_deal_message(deal)
    assert "[PROSSIMAMENTE GRATIS]" in caption
    assert "Upcoming Masterpiece" in caption
    assert "100% GRATIS" in caption
    button = keyboard.inline_keyboard[0][0]
    assert "Vedi su Epic Games" in button.text

def test_caption_length_boundary():
    deal = GameDeal(
        id="long_deal",
        title="A" * 100,
        store="Epic Games",
        stock_price="19,99 €",
        store_url="https://example.com",
        description="Very long text " * 150,
    )
    caption, _ = format_deal_message(deal)
    assert len(caption) <= MAX_CAPTION_LENGTH

def test_settings_formatting():
    enabled_stores = {"Epic Games", "Steam"}
    msg = format_stores_settings_message(enabled_stores)
    assert "2 / 7 store abilitati" in msg

    keyboard = build_stores_keyboard(enabled_stores)
    buttons_flat = [btn for row in keyboard.inline_keyboard for btn in row]
    epic_btn = next(b for b in buttons_flat if "Epic Games" in b.text)
    gog_btn = next(b for b in buttons_flat if "GOG" in b.text)
    assert "✅" in epic_btn.text
    assert "❌" in gog_btn.text

    # Test main and prices menus
    main_msg = format_main_settings_message(2, 5, 10.0, 5.0)
    assert "Store abilitati:</b> 2" in main_msg
    assert "Listino minimo:</b> ≥ 10,00 €" in main_msg

    price_keyboard = build_prices_keyboard(10.0, 5.0)
    price_buttons = [btn for row in price_keyboard.inline_keyboard for btn in row]
    min10_btn = next(b for b in price_buttons if "≥ 10€" in b.text)
    assert "🔘" in min10_btn.text
