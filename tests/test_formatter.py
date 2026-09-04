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
    main_msg = format_main_settings_message(2, 5, 10.0, 5.0, ignore_min_on_free=True, min_rating=70)
    assert "Store abilitati:</b> 2" in main_msg
    assert "Listino minimo:</b> ≥ 10,00 €" in main_msg
    assert "Ignora listino se 100% Gratis:</b> Sì" in main_msg
    assert "≥ 70% positive" in main_msg

    price_keyboard = build_prices_keyboard(10.0, 5.0, ignore_min_on_free=True, min_rating=70)
    price_buttons = [btn for row in price_keyboard.inline_keyboard for btn in row]
    min10_btn = next(b for b in price_buttons if "≥ 10€" in b.text)
    assert "🔘" in min10_btn.text
    toggle_btn = next(b for b in price_buttons if "Ignora listino min se Gratis" in b.text)
    assert "✅" in toggle_btn.text
    rating70_btn = next(b for b in price_buttons if "≥ 70%" in b.text)
    assert "🔘" in rating70_btn.text

def test_deal_with_ratings():
    deal = GameDeal(
        id="rated_game",
        title="Epic Masterpiece",
        store="Steam",
        stock_price="29,99 €",
        store_url="https://store.steampowered.com/app/123",
        rating_percent=92,
        reviews_count=24500,
        genres=["Action", "RPG"],
    )
    caption, _ = format_deal_message(deal)
    assert "⭐ <b>Valutazione:</b> 92% positive (24.500 recensioni)" in caption

def test_settings_subscription_toggle():
    # Test subscribed
    main_msg_sub = format_main_settings_message(2, 5, 10.0, 5.0, ignore_min_on_free=True, min_rating=70, is_subscribed=True)
    assert "🔔 <b>ATTIVE</b>" in main_msg_sub
    kb_sub = build_main_settings_keyboard(is_subscribed=True)
    buttons = [b for row in kb_sub.inline_keyboard for b in row]
    toggle_sub_btn = next(b for b in buttons if b.callback_data == "toggle_sub")
    assert "🔔 Notifiche: ATTIVE" in toggle_sub_btn.text

    # Test unsubscribed
    main_msg_unsub = format_main_settings_message(2, 5, 10.0, 5.0, ignore_min_on_free=True, min_rating=70, is_subscribed=False)
    assert "🔕 <b>DISATTIVATE</b>" in main_msg_unsub
    kb_unsub = build_main_settings_keyboard(is_subscribed=False)
    buttons_unsub = [b for row in kb_unsub.inline_keyboard for b in row]
    toggle_unsub_btn = next(b for b in buttons_unsub if b.callback_data == "toggle_sub")
    assert "🔕 Notifiche: DISATTIVATE" in toggle_unsub_btn.text

def test_format_evening_recap():
    from free_games_bot.formatter import format_evening_recap

    # Test empty deals
    empty_recap = format_evening_recap([])
    assert len(empty_recap) == 1
    assert "Nessuna offerta pertinente attiva al momento" in empty_recap[0]

    # Test populated deals: 1 free, 1 discounted
    free_deal = GameDeal(
        id="free-1",
        title="Death Stranding",
        store="Epic Games",
        stock_price="39,99 €",
        sale_price_value=0.0,
        store_url="https://store.epicgames.com/death-stranding",
        rating_percent=93,
        reviews_count=85000,
        genres=["Action", "Adventure"],
    )
    discounted_deal = GameDeal(
        id="disc-1",
        title="Cyberpunk 2077",
        store="Steam",
        stock_price="59,99 €",
        sale_price_value=29.99,
        store_url="https://store.steampowered.com/app/1091500",
        rating_percent=89,
        reviews_count=650000,
        genres=["RPG", "Action"],
    )

    chunks = format_evening_recap([free_deal, discounted_deal])
    assert len(chunks) == 1
    text = chunks[0]

    # Check headers
    assert "RECAP SERALE OFFERTE" in text
    assert "GIOCHI GRATUITI" in text
    assert "OFFERTE SCONTATE" in text

    # Check free game formatting: link text "Riscatta su Epic Games"
    assert "Death Stranding" in text
    assert "Riscatta su Epic Games" in text
    assert "39,99 €" in text
    assert "93%" in text

    # Check discounted game formatting: link text "Vedi su Steam"
    assert "Cyberpunk 2077" in text
    assert "Vedi su Steam" in text
    assert "-50%" in text
    assert "29,99 €" in text
    assert "89%" in text

    # Check category icons (Action -> ⚔️ or RPG -> 🛡️)
    assert "⚔️" in text or "🛡️" in text
