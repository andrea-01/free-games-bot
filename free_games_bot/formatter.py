"""Message formatting and inline keyboard builder for Telegram."""
import html
from typing import Tuple, Set
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from free_games_bot.models import GameDeal
from free_games_bot.database import ALL_STORES

# Telegram photo caption character limit is 1024
MAX_CAPTION_LENGTH = 1024

def format_deal_message(deal: GameDeal) -> Tuple[str, InlineKeyboardMarkup]:
    """Format a GameDeal into a Telegram HTML message with an inline keyboard."""
    clean_title = html.escape(deal.clean_title())
    store_name = html.escape(deal.store)
    stock_price = html.escape(deal.stock_price)

    lines = []

    if deal.is_upcoming:
        lines.append("⏳ <b>[UPCOMING FREE GAME]</b>")
        lines.append(f"🎮 <b>{clean_title}</b>")
        lines.append(f"🏬 <b>Store:</b> {store_name}")
        if stock_price and stock_price != "Free":
            lines.append(f"💰 <b>Regular Price:</b> {stock_price} (Will be 100% OFF)")
        if deal.end_date:
            lines.append(f"⏰ <b>Schedule:</b> {html.escape(deal.end_date)}")
    else:
        lines.append("🎉 <b>FREE GAME ALERT</b> 🎉")
        lines.append(f"🎮 <b>{clean_title}</b>")
        lines.append(f"🏬 <b>Store:</b> {store_name}")
        if stock_price and stock_price != "Free":
            lines.append(f"💰 <b>Stock Price:</b> <s>{stock_price}</s> ➔ <b>FREE (100% OFF)</b>")
        else:
            lines.append(f"💰 <b>Price:</b> <b>FREE (100% OFF)</b>")

        if deal.end_date:
            lines.append(f"⏳ <b>Offer Ends:</b> {html.escape(deal.end_date)}")

    # Metadata lines
    meta_lines = []
    if deal.release_year:
        meta_lines.append(f"📅 <b>Year:</b> {html.escape(deal.release_year)}")

    if deal.genres:
        genres_str = ", ".join(deal.genres[:4])
        meta_lines.append(f"🏷️ <b>Genres:</b> {html.escape(genres_str)}")

    if deal.player_modes:
        modes_str = ", ".join(deal.player_modes[:3])
        meta_lines.append(f"👥 <b>Modes:</b> {html.escape(modes_str)}")

    if meta_lines:
        lines.append("")
        lines.extend(meta_lines)

    # Description (truncated to ensure within Telegram caption limit)
    if deal.description:
        desc = deal.description.strip()
        max_desc_len = 300
        if len(desc) > max_desc_len:
            desc = desc[:max_desc_len].rsplit(" ", 1)[0] + "..."
        lines.append("")
        lines.append(f"📖 <i>{html.escape(desc)}</i>")

    caption = "\n".join(lines)
    if len(caption) > MAX_CAPTION_LENGTH:
        caption = caption[:MAX_CAPTION_LENGTH - 3] + "..."

    # Keyboard button
    button_text = f"🎮 Claim on {deal.store}" if not deal.is_upcoming else f"👀 View on {deal.store}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text=button_text, url=deal.store_url)]
    ])

    return caption, keyboard

def format_settings_message(enabled_stores: Set[str]) -> str:
    """Create the text message for the /settings command."""
    count = len(enabled_stores)
    return (
        "⚙️ <b>Store Preferences</b>\n\n"
        "Select the stores you want to receive alerts for.\n"
        "Tap a button below to toggle that store on/off.\n\n"
        f"📊 <b>Active Subscriptions:</b> {count} / {len(ALL_STORES)} stores enabled."
    )

def build_settings_keyboard(enabled_stores: Set[str]) -> InlineKeyboardMarkup:
    """Build an interactive inline keyboard to toggle stores."""
    buttons = []
    row = []

    for store in ALL_STORES:
        is_enabled = store in enabled_stores
        icon = "✅" if is_enabled else "❌"
        text = f"{icon} {store}"
        callback_data = f"toggle:{store}"
        row.append(InlineKeyboardButton(text=text, callback_data=callback_data))

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    # Action row: Select All / Deselect All
    buttons.append([
        InlineKeyboardButton(text="🔔 Enable All", callback_data="preset:all"),
        InlineKeyboardButton(text="🔕 Disable All", callback_data="preset:none"),
    ])

    return InlineKeyboardMarkup(buttons)
