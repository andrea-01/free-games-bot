"""Message formatting and inline keyboard builder in Italian for Telegram."""
import html
from typing import Tuple, Set, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from free_games_bot.models import GameDeal, format_price_eur
from free_games_bot.database import ALL_STORES, ALL_CATEGORIES

# Telegram photo caption character limit is 1024
MAX_CAPTION_LENGTH = 1024

def format_deal_message(deal: GameDeal) -> Tuple[str, InlineKeyboardMarkup]:
    """Format a GameDeal into an Italian Telegram HTML message with an inline keyboard."""
    clean_title = html.escape(deal.clean_title())
    store_name = html.escape(deal.store)
    stock_price = html.escape(deal.stock_price)

    lines = []

    if deal.is_upcoming:
        lines.append("⏳ <b>[PROSSIMAMENTE GRATIS]</b>")
        lines.append(f"🎮 <b>{clean_title}</b>")
        lines.append(f"🏬 <b>Store:</b> {store_name}")
        if stock_price and stock_price != "Gratis":
            lines.append(f"💰 <b>Valore di listino:</b> {stock_price} (Sarà 100% GRATIS)")
        if deal.end_date:
            lines.append(f"⏰ <b>Date:</b> {html.escape(deal.end_date)}")
    elif deal.sale_price_value > 0.01:
        # Discounted deal
        lines.append("🔥 <b>OFFERTA PC</b> 🔥")
        lines.append(f"🎮 <b>{clean_title}</b>")
        lines.append(f"🏬 <b>Store:</b> {store_name}")
        sale_str = format_price_eur(deal.sale_price_value)
        if deal.stock_price_value > deal.sale_price_value:
            discount = int(round((1 - (deal.sale_price_value / deal.stock_price_value)) * 100))
            lines.append(f"💰 <b>Prezzo:</b> <s>{stock_price}</s> ➔ <b>{sale_str}</b> (-{discount}%)")
        else:
            lines.append(f"💰 <b>Prezzo in offerta:</b> <b>{sale_str}</b>")
    else:
        # 100% Free deal
        lines.append("🎉 <b>GIOCO GRATIS</b> 🎉")
        lines.append(f"🎮 <b>{clean_title}</b>")
        lines.append(f"🏬 <b>Store:</b> {store_name}")
        if stock_price and stock_price != "Gratis":
            lines.append(f"💰 <b>Prezzo di listino:</b> <s>{stock_price}</s> ➔ <b>GRATIS (100% di sconto)</b>")
        else:
            lines.append("💰 <b>Prezzo:</b> <b>GRATIS (100% di sconto)</b>")

        if deal.end_date:
            lines.append(f"⏳ <b>Termina il:</b> {html.escape(deal.end_date)}")

    # Metadata lines (sempre visualizzati!)
    lines.append("")
    year_str = deal.release_year if deal.release_year else "N/D"
    lines.append(f"📅 <b>Anno:</b> {html.escape(year_str)}")

    genres_str = ", ".join(deal.genres[:4]) if deal.genres else "Indie / Generale"
    lines.append(f"🏷️ <b>Generi:</b> {html.escape(genres_str)}")

    modes_str = ", ".join(deal.player_modes[:3]) if deal.player_modes else "Giocatore singolo"
    lines.append(f"👥 <b>Modalità:</b> {html.escape(modes_str)}")

    # Description (sempre visualizzata)
    desc = (deal.description or f"Approfitta dell'offerta per {deal.clean_title()} disponibile su {deal.store}.").strip()
    max_desc_len = 320
    if len(desc) > max_desc_len:
        desc = desc[:max_desc_len].rsplit(" ", 1)[0] + "..."
    lines.append("")
    lines.append(f"📖 <i>{html.escape(desc)}</i>")

    caption = "\n".join(lines)
    if len(caption) > MAX_CAPTION_LENGTH:
        caption = caption[:MAX_CAPTION_LENGTH - 3] + "..."

    # Keyboard button
    if deal.is_upcoming:
        button_text = f"👀 Vedi su {deal.store}"
    elif deal.sale_price_value > 0.01:
        button_text = f"🛒 Vedi Offerta su {deal.store}"
    else:
        button_text = f"🎮 Riscatta su {deal.store}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text=button_text, url=deal.store_url)]
    ])

    return caption, keyboard

# --- Settings Menus ---

def format_main_settings_message(stores_count: int, cats_count: int, min_stock: float, max_sale: float) -> str:
    """Main settings overview message."""
    min_stock_str = f"≥ {min_stock:.2f}".replace(".", ",") + " €" if min_stock > 0 else "Nessun limite (Tutti)"
    max_sale_str = f"≤ {max_sale:.2f}".replace(".", ",") + " €" if max_sale > 0 else "Solo Gratis (0,00 €)"

    return (
        "⚙️ <b>Impostazioni & Filtri</b>\n\n"
        "Personalizza quali notifiche e giochi visualizzare:\n\n"
        f"🏬 <b>Store abilitati:</b> {stores_count} / {len(ALL_STORES)}\n"
        f"🏷️ <b>Categorie abilitate:</b> {cats_count} / {len(ALL_CATEGORIES)}\n"
        f"💰 <b>Listino minimo:</b> {min_stock_str}\n"
        f"🏷️ <b>Prezzo max offerta:</b> {max_sale_str}\n\n"
        "<i>Seleziona una sezione qui sotto per modificarla:</i>"
    )

def build_main_settings_keyboard() -> InlineKeyboardMarkup:
    """Main settings menu keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text="🏬 Store", callback_data="nav:stores"),
            InlineKeyboardButton(text="🏷️ Categorie", callback_data="nav:categories"),
        ],
        [
            InlineKeyboardButton(text="💰 Prezzi & Soglie", callback_data="nav:prices"),
        ],
        [
            InlineKeyboardButton(text="✅ Chiudi", callback_data="nav:close"),
        ]
    ])

# --- Stores Submenu ---

def format_stores_settings_message(enabled_stores: Set[str]) -> str:
    count = len(enabled_stores)
    return (
        "🏬 <b>Filtro Store</b>\n\n"
        "Tocca uno store per abilitarlo o disabilitarlo:\n\n"
        f"📊 <b>Stato:</b> {count} / {len(ALL_STORES)} store abilitati."
    )

def build_stores_keyboard(enabled_stores: Set[str]) -> InlineKeyboardMarkup:
    buttons = []
    row = []

    for store in ALL_STORES:
        is_enabled = store in enabled_stores
        icon = "✅" if is_enabled else "❌"
        text = f"{icon} {store}"
        callback_data = f"toggle_store:{store}"
        row.append(InlineKeyboardButton(text=text, callback_data=callback_data))

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text="🔔 Abilita Tutti", callback_data="preset_store:all"),
        InlineKeyboardButton(text="🔕 Disabilita Tutti", callback_data="preset_store:none"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Torna alle Impostazioni", callback_data="nav:main"),
    ])

    return InlineKeyboardMarkup(buttons)

# --- Categories Submenu ---

def format_categories_settings_message(enabled_categories: Set[str]) -> str:
    count = len(enabled_categories)
    return (
        "🏷️ <b>Filtro Categorie</b>\n\n"
        "Tocca una categoria per abilitarla o disabilitarla:\n\n"
        f"📊 <b>Stato:</b> {count} / {len(ALL_CATEGORIES)} categorie abilitate."
    )

def build_categories_keyboard(enabled_categories: Set[str]) -> InlineKeyboardMarkup:
    buttons = []
    row = []

    for cat in ALL_CATEGORIES:
        is_enabled = cat in enabled_categories
        icon = "✅" if is_enabled else "❌"
        text = f"{icon} {cat}"
        callback_data = f"toggle_cat:{cat}"
        row.append(InlineKeyboardButton(text=text, callback_data=callback_data))

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text="🔔 Abilita Tutte", callback_data="preset_cat:all"),
        InlineKeyboardButton(text="🔕 Disabilita Tutte", callback_data="preset_cat:none"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Torna alle Impostazioni", callback_data="nav:main"),
    ])

    return InlineKeyboardMarkup(buttons)

# --- Prices Submenu ---

def format_prices_settings_message(min_stock: float, max_sale: float) -> str:
    min_stock_str = f"{min_stock:.2f}".replace(".", ",") + " €" if min_stock > 0 else "Disattivo (Qualsiasi listino)"
    max_sale_str = f"{max_sale:.2f}".replace(".", ",") + " €" if max_sale > 0 else "0,00 € (Solo 100% GRATIS)"

    return (
        "💰 <b>Filtro Prezzi & Offerte</b>\n\n"
        f"• <b>Listino Minimo Attuale:</b> {min_stock_str}\n"
        "  <i>(Esclude giochi con valore originale inferiore a questa soglia)</i>\n\n"
        f"• <b>Prezzo Massimo in Offerta:</b> {max_sale_str}\n"
        "  <i>(Se 0€ ricevi solo giochi 100% gratis. Se > 0€ include anche offerte sotto questo prezzo)</i>\n\n"
        "<i>Tocca un'opzione qui sotto per impostare le soglie rapide, o usa /minprice e /maxprice:</i>"
    )

def build_prices_keyboard(min_stock: float, max_sale: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        # Row 1: Min stock price label
        [InlineKeyboardButton(text="🏷️ Listino Minimo:", callback_data="noop")],
        [
            InlineKeyboardButton(text=f"{'🔘' if min_stock == 0 else '⚪️'} Qualsiasi (0€)", callback_data="set_min:0"),
            InlineKeyboardButton(text=f"{'🔘' if min_stock == 5 else '⚪️'} ≥ 5€", callback_data="set_min:5"),
            InlineKeyboardButton(text=f"{'🔘' if min_stock == 10 else '⚪️'} ≥ 10€", callback_data="set_min:10"),
        ],
        [
            InlineKeyboardButton(text=f"{'🔘' if min_stock == 15 else '⚪️'} ≥ 15€", callback_data="set_min:15"),
            InlineKeyboardButton(text=f"{'🔘' if min_stock == 20 else '⚪️'} ≥ 20€", callback_data="set_min:20"),
            InlineKeyboardButton(text=f"{'🔘' if min_stock == 30 else '⚪️'} ≥ 30€", callback_data="set_min:30"),
        ],
        # Row 2: Max sale price label
        [InlineKeyboardButton(text="🏷️ Prezzo Max Scontato:", callback_data="noop")],
        [
            InlineKeyboardButton(text=f"{'🔘' if max_sale == 0 else '⚪️'} Solo Gratis (0€)", callback_data="set_max:0"),
            InlineKeyboardButton(text=f"{'🔘' if max_sale == 2 else '⚪️'} ≤ 2€", callback_data="set_max:2"),
            InlineKeyboardButton(text=f"{'🔘' if max_sale == 5 else '⚪️'} ≤ 5€", callback_data="set_max:5"),
        ],
        [
            InlineKeyboardButton(text=f"{'🔘' if max_sale == 10 else '⚪️'} ≤ 10€", callback_data="set_max:10"),
            InlineKeyboardButton(text=f"{'🔘' if max_sale == 15 else '⚪️'} ≤ 15€", callback_data="set_max:15"),
            InlineKeyboardButton(text="🔄 Reset Prezzi", callback_data="reset_prices"),
        ],
        [
            InlineKeyboardButton(text="🔙 Torna alle Impostazioni", callback_data="nav:main"),
        ]
    ])
