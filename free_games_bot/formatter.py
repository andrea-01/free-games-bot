import html
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Tuple, Set, Optional, List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from free_games_bot.models import GameDeal, format_price_eur
from free_games_bot.database import ALL_STORES, ALL_CATEGORIES, normalize_deal_category

# Icone per le categorie per il recap serale
CATEGORY_ICONS = {
    "Azione": "⚔️",
    "Avventura": "🗺️",
    "GDR / RPG": "🛡️",
    "Strategia": "♟️",
    "Sparatutto": "🎯",
    "Corse": "🏎️",
    "Sport": "⚽",
    "Simulazione": "✈️",
    "Puzzle": "🧩",
    "Horror": "🧟",
    "Indie": "👾",
    "Altro": "🎮",
}

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

    if deal.rating_percent is not None:
        rating_str = f"⭐ <b>Valutazione:</b> {deal.rating_percent}% positive"
        if deal.reviews_count:
            count_str = f"{deal.reviews_count:,}".replace(",", ".")
            rating_str += f" ({count_str} recensioni)"
        lines.append(rating_str)

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

def format_main_settings_message(
    stores_count: int,
    cats_count: int,
    min_stock: float,
    max_sale: float,
    ignore_min_on_free: bool = True,
    min_rating: int = 0,
    is_subscribed: bool = True,
) -> str:
    """Main settings overview message with subscription status."""
    sub_status_str = "🔔 <b>ATTIVE</b> (Ricevi notifiche e recap serale)" if is_subscribed else "🔕 <b>DISATTIVATE</b> (Nessuna notifica automatica)"
    min_stock_str = f"≥ {min_stock:.2f}".replace(".", ",") + " €" if min_stock > 0 else "Nessun limite (Tutti)"
    max_sale_str = f"≤ {max_sale:.2f}".replace(".", ",") + " €" if max_sale > 0 else "Solo Gratis (0,00 €)"
    ignore_free_str = "Sì (Sempre visibili)" if ignore_min_on_free else "No (Filtro attivo anche sui gratis)"
    rating_str = f"≥ {min_rating}% positive" if min_rating > 0 else "Disattivo (Tutti i giochi)"

    return (
        "⚙️ <b>Impostazioni & Filtri</b>\n\n"
        "Personalizza quali notifiche e giochi visualizzare:\n\n"
        f"📢 <b>Notifiche:</b> {sub_status_str}\n"
        f"🏬 <b>Store abilitati:</b> {stores_count} / {len(ALL_STORES)}\n"
        f"🏷️ <b>Categorie abilitate:</b> {cats_count} / {len(ALL_CATEGORIES)}\n"
        f"💰 <b>Listino minimo:</b> {min_stock_str}\n"
        f"🏷️ <b>Prezzo max offerta:</b> {max_sale_str}\n"
        f"🎁 <b>Ignora listino se 100% Gratis:</b> {ignore_free_str}\n"
        f"⭐ <b>Filtro qualità/anti-spam:</b> {rating_str}\n\n"
        "<i>Tocca un pulsante qui sotto per attivare/disattivare le notifiche o modificare i filtri:</i>"
    )

def build_main_settings_keyboard(is_subscribed: bool = True) -> InlineKeyboardMarkup:
    """Main settings menu keyboard with notification toggle."""
    toggle_text = "🔔 Notifiche: ATTIVE (Tocca per disattivare)" if is_subscribed else "🔕 Notifiche: DISATTIVATE (Tocca per attivare)"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text=toggle_text, callback_data="toggle_sub"),
        ],
        [
            InlineKeyboardButton(text="🏬 Store", callback_data="nav:stores"),
            InlineKeyboardButton(text="🏷️ Categorie", callback_data="nav:categories"),
        ],
        [
            InlineKeyboardButton(text="💰 Prezzi & Filtro Qualità", callback_data="nav:prices"),
        ],
        [
            InlineKeyboardButton(text="✅ Chiudi", callback_data="nav:close"),
        ]
    ])

def format_evening_recap(
    deals: List[GameDeal],
    is_nofilter: bool = False,
    is_manual: bool = False,
) -> List[str]:
    """
    Format active deals into a compact recap list (divided into Free and Discounted).
    Each game occupies at most 2 lines:
    Line 1: [Icon] [Title] • [Price / Discount]
    Line 2: [⭐ Rating] • [Riscatta/Vedi su Store link]
    Returns list of message chunks (respecting Telegram's 4096 char limit).
    """
    free_deals = [d for d in deals if d.sale_price_value <= 0.01 and not d.is_upcoming]
    discounted_deals = [d for d in deals if d.sale_price_value > 0.01 and not d.is_upcoming]

    now_rome = datetime.now(ZoneInfo("Europe/Rome"))
    date_str = now_rome.strftime("%d/%m/%Y")
    datetime_str = now_rome.strftime("%d/%m/%Y, %H:%M")

    if is_nofilter:
        header = (
            f"🌍 <b>RECAP OFFERTE PC (SENZA FILTRI)</b> — <i>{datetime_str}</i>\n"
            "<i>Ecco l'elenco completo di tutte le offerte e giochi gratis attivi senza filtri:</i>\n\n"
        )
        footer = "\n💡 <i>Visualizza il recap personalizzato secondo i tuoi filtri con /recap</i>"
    elif is_manual:
        header = (
            f"📊 <b>RECAP OFFERTE PC</b> — <i>{datetime_str}</i>\n"
            "<i>Ecco il riepilogo delle migliori offerte attive secondo i tuoi filtri:</i>\n\n"
        )
        footer = "\n💡 <i>Personalizza i tuoi filtri o disattiva le notifiche con /settings</i>"
    else:
        header = (
            f"🌙 <b>RECAP SERALE OFFERTE PC</b> — <i>{date_str}</i>\n"
            "<i>Ecco il riepilogo serale delle migliori offerte attive secondo i tuoi filtri:</i>\n\n"
        )
        footer = "\n💡 <i>Personalizza o disattiva il recap serale dalle impostazioni con /settings</i>"

    items: List[str] = []

    if free_deals:
        items.append(f"🎁 <b>GIOCHI GRATUITI ({len(free_deals)})</b>\n")
        for deal in free_deals:
            cat = normalize_deal_category(deal.genres[0]) if deal.genres else "Altro"
            icon = CATEGORY_ICONS.get(cat, "🎮")
            title = deal.clean_title()
            if len(title) > 36:
                title = title[:33].rstrip() + "..."
            title_esc = html.escape(title)

            if deal.stock_price and deal.stock_price != "Gratis":
                price_str = f"<s>{html.escape(deal.stock_price)}</s> ➔ <b>GRATIS</b>"
            else:
                price_str = "<b>GRATIS (100%)</b>"

            line1 = f"{icon} <b>{title_esc}</b> • {price_str}"

            link_html = f'<a href="{html.escape(deal.store_url)}">Riscatta su {html.escape(deal.store)}</a>'
            if deal.rating_percent is not None:
                if deal.reviews_count and deal.reviews_count >= 1000:
                    c_str = f"{deal.reviews_count / 1000:.1f}k".replace(".0k", "k")
                elif deal.reviews_count:
                    c_str = str(deal.reviews_count)
                else:
                    c_str = None
                r_part = f"⭐ {deal.rating_percent}%" + (f" ({c_str})" if c_str else "")
                line2 = f"{r_part} • {link_html}"
            else:
                line2 = f"🏷️ {html.escape(cat)} • {link_html}"

            items.append(f"{line1}\n{line2}\n")

    if discounted_deals:
        if free_deals:
            items.append("\n")
        items.append(f"🔥 <b>OFFERTE SCONTATE ({len(discounted_deals)})</b>\n")
        for deal in discounted_deals:
            cat = normalize_deal_category(deal.genres[0]) if deal.genres else "Altro"
            icon = CATEGORY_ICONS.get(cat, "🎮")
            title = deal.clean_title()
            if len(title) > 36:
                title = title[:33].rstrip() + "..."
            title_esc = html.escape(title)

            sale_str = format_price_eur(deal.sale_price_value)
            if deal.stock_price_value > deal.sale_price_value:
                discount = int(round((1 - (deal.sale_price_value / deal.stock_price_value)) * 100))
                price_str = f"<s>{html.escape(deal.stock_price)}</s> ➔ <b>{sale_str}</b> (-{discount}%)"
            else:
                price_str = f"<b>{sale_str}</b>"

            line1 = f"{icon} <b>{title_esc}</b> • {price_str}"

            link_html = f'<a href="{html.escape(deal.store_url)}">Vedi su {html.escape(deal.store)}</a>'
            if deal.rating_percent is not None:
                if deal.reviews_count and deal.reviews_count >= 1000:
                    c_str = f"{deal.reviews_count / 1000:.1f}k".replace(".0k", "k")
                elif deal.reviews_count:
                    c_str = str(deal.reviews_count)
                else:
                    c_str = None
                r_part = f"⭐ {deal.rating_percent}%" + (f" ({c_str})" if c_str else "")
                line2 = f"{r_part} • {link_html}"
            else:
                line2 = f"🏷️ {html.escape(cat)} • {link_html}"

            items.append(f"{line1}\n{line2}\n")

    if not items:
        empty_msg = "ℹ️ Nessuna offerta attiva trovata al momento.\n" if is_nofilter else "ℹ️ Nessuna offerta pertinente attiva al momento secondo i tuoi filtri.\n"
        return [header + empty_msg + footer]

    chunks: List[str] = []
    current_chunk = header
    for item in items:
        if len(current_chunk) + len(item) + len(footer) > 3800:
            chunks.append(current_chunk)
            current_chunk = item
        else:
            current_chunk += item

    current_chunk += footer
    chunks.append(current_chunk)

    return chunks

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

def format_prices_settings_message(
    min_stock: float,
    max_sale: float,
    ignore_min_on_free: bool = True,
    min_rating: int = 0
) -> str:
    min_stock_str = f"{min_stock:.2f}".replace(".", ",") + " €" if min_stock > 0 else "Disattivo (Qualsiasi listino)"
    max_sale_str = f"{max_sale:.2f}".replace(".", ",") + " €" if max_sale > 0 else "0,00 € (Solo 100% GRATIS)"
    ignore_status = "✅ <b>ATTIVO</b> (I giochi gratuiti non verranno mai nascosti dal listino min)" if ignore_min_on_free else "❌ <b>DISATTIVO</b> (Anche i giochi gratis devono rispettare il listino min)"
    rating_status = f"⭐ <b>≥ {min_rating}%</b> positive (Blocca shovelware/spam)" if min_rating > 0 else "⚪️ <b>Nessun filtro qualità</b>"

    return (
        "💰 <b>Filtro Prezzi & Qualità Offerte</b>\n\n"
        f"• <b>Listino Minimo:</b> {min_stock_str}\n"
        "  <i>(Esclude offerte con prezzo originale inferiore a questa cifra)</i>\n\n"
        f"• <b>Prezzo Massimo in Offerta:</b> {max_sale_str}\n"
        "  <i>(0€ = solo giochi 100% gratis. Altrimenti include sconti sotto questo importo)</i>\n\n"
        f"• <b>Ignora Listino per Giochi 100% Gratis:</b>\n"
        f"  {ignore_status}\n\n"
        f"• <b>Filtro Qualità / Anti-Spam:</b>\n"
        f"  {rating_status}\n\n"
        "<i>Tocca i pulsanti per modificare le opzioni:</i>"
    )

def build_prices_keyboard(
    min_stock: float,
    max_sale: float,
    ignore_min_on_free: bool = True,
    min_rating: int = 0
) -> InlineKeyboardMarkup:
    toggle_icon = "✅" if ignore_min_on_free else "❌"
    toggle_label = f"{toggle_icon} Ignora listino min se Gratis"

    return InlineKeyboardMarkup([
        # Row 1: Min stock price
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
        # Row 2: Free toggle
        [
            InlineKeyboardButton(text=toggle_label, callback_data="toggle_ignore_min_free")
        ],
        # Row 3: Max sale price
        [InlineKeyboardButton(text="🏷️ Prezzo Max in Offerta:", callback_data="noop")],
        [
            InlineKeyboardButton(text=f"{'🔘' if max_sale == 0 else '⚪️'} Solo Gratis (0€)", callback_data="set_max:0"),
            InlineKeyboardButton(text=f"{'🔘' if max_sale == 2 else '⚪️'} ≤ 2€", callback_data="set_max:2"),
            InlineKeyboardButton(text=f"{'🔘' if max_sale == 5 else '⚪️'} ≤ 5€", callback_data="set_max:5"),
        ],
        [
            InlineKeyboardButton(text=f"{'🔘' if max_sale == 10 else '⚪️'} ≤ 10€", callback_data="set_max:10"),
            InlineKeyboardButton(text=f"{'🔘' if max_sale == 15 else '⚪️'} ≤ 15€", callback_data="set_max:15"),
        ],
        # Row 4: Quality / Rating Anti-Spam filter
        [InlineKeyboardButton(text="⭐ Filtro Qualità / Anti-Spam:", callback_data="noop")],
        [
            InlineKeyboardButton(text=f"{'🔘' if min_rating == 0 else '⚪️'} Qualsiasi", callback_data="set_min_rating:0"),
            InlineKeyboardButton(text=f"{'🔘' if min_rating == 70 else '⚪️'} ⭐ ≥ 70%", callback_data="set_min_rating:70"),
            InlineKeyboardButton(text=f"{'🔘' if min_rating == 80 else '⚪️'} ⭐ ≥ 80%", callback_data="set_min_rating:80"),
        ],
        # Row 5: Reset & Return
        [
            InlineKeyboardButton(text="🔄 Reset Filtri Prezzo & Qualità", callback_data="reset_prices"),
        ],
        [
            InlineKeyboardButton(text="🔙 Torna alle Impostazioni", callback_data="nav:main"),
        ]
    ])
