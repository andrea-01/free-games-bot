"""Telegram bot handlers, store preferences, and background periodic deal notifier."""
import json
import logging
from typing import Optional, Set
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from free_games_bot.config import config
from free_games_bot.database import Database, ALL_STORES
from free_games_bot.fetchers.manager import DealManager
from free_games_bot.formatter import (
    format_deal_message,
    format_settings_message,
    build_settings_keyboard,
)
from free_games_bot.models import GameDeal

logger = logging.getLogger(__name__)

async def send_deal_message(bot, chat_id: int, deal: GameDeal):
    """Send a deal to a chat with its cover image, falling back to text if image fails."""
    caption, reply_markup = format_deal_message(deal)

    if deal.cover_url:
        try:
            await bot.send_photo(
                chat_id=chat_id,
                photo=deal.cover_url,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
            return
        except Exception as e:
            logger.warning(f"Failed to send deal photo ({deal.cover_url}) to {chat_id}: {e}. Falling back to text message.")

    # Fallback to plain text message
    await bot.send_message(
        chat_id=chat_id,
        text=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
        disable_web_page_preview=False,
    )

class FreeGamesBot:
    def __init__(self, db: Optional[Database] = None, deal_manager: Optional[DealManager] = None):
        self.db = db or Database()
        self.deal_manager = deal_manager or DealManager()
        self.app: Optional[Application] = None

    async def init(self):
        """Initialize database and internal services."""
        await self.db.init_db()

    def build_application(self) -> Application:
        """Create and configure Telegram Application."""
        if not config.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment or .env file.")

        builder = ApplicationBuilder().token(config.telegram_bot_token)
        app = builder.build()

        # Register command handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler(["free", "deals"], self.free_command))
        app.add_handler(CommandHandler("epic", self.epic_command))
        app.add_handler(CommandHandler("steam", self.steam_command))
        app.add_handler(CommandHandler("check", self.check_command))
        app.add_handler(CommandHandler("settings", self.settings_command))
        app.add_handler(CommandHandler("subscribe", self.subscribe_command))
        app.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))

        # Register callback query handlers for interactive store toggle buttons
        app.add_handler(CallbackQueryHandler(self.settings_callback, pattern=r"^(toggle|preset):"))

        # Register global error handler
        app.add_error_handler(self.error_handler)

        # Setup background periodic checker
        if app.job_queue:
            interval_seconds = max(60, config.check_interval_minutes * 60)
            app.job_queue.run_repeating(
                self.periodic_check_job,
                interval=interval_seconds,
                first=10,
                name="periodic_deal_checker",
            )
            logger.info(f"Scheduled periodic deal checker every {config.check_interval_minutes} minutes.")

        self.app = app
        return app

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error that occurred during an update."""
        logger.error("Exception occurred while handling an update:", exc_info=context.error)

    # --- Command Handlers ---

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        chat_id = update.effective_chat.id

        await self.db.add_subscriber(
            chat_id=chat_id,
            username=user.username if user else None,
            first_name=user.first_name if user else None,
        )

        welcome_text = (
            f"👋 <b>Welcome, {user.first_name if user else 'Gamer'}!</b>\n\n"
            "🎮 <b>Free PC Games Deal Bot</b> is active.\n"
            "I monitor Epic Games, Steam, GOG, Ubisoft, EA, and more for 100% free PC game giveaways.\n\n"
            "✨ <b>Features:</b>\n"
            "• High-resolution cover art (via SteamGridDB)\n"
            "• Original stock price & discount value\n"
            "• Full metadata (Release year, single/multiplayer, genres)\n"
            "• 1-click claim button directly to the store\n"
            "• Customizable store filters (/settings)\n"
            "• Automatic alerts for newly dropped free games\n\n"
            "📌 <b>Available Commands:</b>\n"
            "/free - View all current free PC games\n"
            "/settings - Choose which stores you want to receive deals from\n"
            "/epic - View Epic Games free & upcoming giveaways\n"
            "/steam - View Steam free promotions\n"
            "/check - Check for newly released giveaways\n"
            "/subscribe - Enable automatic deal notifications\n"
            "/unsubscribe - Disable deal notifications\n"
            "/help - Show command guide"
        )
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            "🛠 <b>Free Games Bot Commands:</b>\n\n"
            "/free or /deals - Fetch all active free game giveaways across your enabled stores\n"
            "/settings - Toggle which stores you want to receive alerts from\n"
            "/epic - View active & upcoming free games on Epic Games Store\n"
            "/steam - View free game deals on Steam\n"
            "/check - Scan for new deals not yet sent to you\n"
            "/subscribe - Turn on automatic background alerts\n"
            "/unsubscribe - Stop automated alerts\n"
            "/help - View command instructions\n\n"
            "💡 <i>Tip: Tap the 'Claim' button under any deal to open its official store page.</i>"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command: show interactive store preference buttons."""
        chat_id = update.effective_chat.id
        enabled_stores = await self.db.get_user_stores(chat_id)
        text = format_settings_message(enabled_stores)
        keyboard = build_settings_keyboard(enabled_stores)
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    async def settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from the /settings store toggle buttons."""
        query = update.callback_query
        await query.answer()

        chat_id = query.message.chat.id
        data = query.data

        if data.startswith("toggle:"):
            store = data.split(":", 1)[1]
            enabled_stores = await self.db.toggle_user_store(chat_id, store)
        elif data == "preset:all":
            enabled_stores = await self.db.set_user_stores(chat_id, set(ALL_STORES))
        elif data == "preset:none":
            enabled_stores = await self.db.set_user_stores(chat_id, set())
        else:
            return

        new_text = format_settings_message(enabled_stores)
        new_keyboard = build_settings_keyboard(enabled_stores)

        try:
            await query.edit_message_text(text=new_text, reply_markup=new_keyboard, parse_mode=ParseMode.HTML)
        except Exception:
            pass  # Message content unchanged

    async def free_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /free or /deals command."""
        chat_id = update.effective_chat.id
        status_msg = await update.message.reply_text("🔍 <i>Searching PC game stores for active free games...</i>", parse_mode=ParseMode.HTML)

        all_deals = await self.deal_manager.get_active_deals()
        user_stores = await self.db.get_user_stores(chat_id)

        # Filter by user's enabled stores
        deals = [
            deal for deal in all_deals
            if await self.db.is_deal_allowed_for_user(chat_id, deal.store)
        ]

        if not deals:
            if not user_stores:
                await status_msg.edit_text("⚠️ You have disabled all stores in /settings! Please enable at least one store to view deals.")
            else:
                await status_msg.edit_text("ℹ️ No active free games found for your selected stores right now. Use /settings to enable more stores!")
            return

        await status_msg.edit_text(f"🎁 Found <b>{len(deals)}</b> free game deals for your stores! Sending them now...", parse_mode=ParseMode.HTML)

        for deal in deals:
            await send_deal_message(context.bot, chat_id, deal)
            await self.db.mark_deal_sent(deal.id, chat_id, deal.title, deal.store)

    async def epic_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /epic command."""
        chat_id = update.effective_chat.id
        status_msg = await update.message.reply_text("🔍 <i>Fetching Epic Games Store giveaways...</i>", parse_mode=ParseMode.HTML)

        deals = await self.deal_manager.get_epic_deals()

        if not deals:
            await status_msg.edit_text("ℹ️ No Epic Games giveaways found at this time.")
            return

        await status_msg.edit_text(f"🎁 Found <b>{len(deals)}</b> Epic Games promotion(s):", parse_mode=ParseMode.HTML)

        for deal in deals:
            await send_deal_message(context.bot, chat_id, deal)
            await self.db.mark_deal_sent(deal.id, chat_id, deal.title, deal.store)

    async def steam_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /steam command."""
        chat_id = update.effective_chat.id
        status_msg = await update.message.reply_text("🔍 <i>Fetching Steam giveaways...</i>", parse_mode=ParseMode.HTML)

        deals = await self.deal_manager.get_steam_deals()

        if not deals:
            await status_msg.edit_text("ℹ️ No 100% free Steam game deals found right now.")
            return

        await status_msg.edit_text(f"🎁 Found <b>{len(deals)}</b> Steam promotion(s):", parse_mode=ParseMode.HTML)

        for deal in deals:
            await send_deal_message(context.bot, chat_id, deal)
            await self.db.mark_deal_sent(deal.id, chat_id, deal.title, deal.store)

    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check command: check for deals not yet received by the user."""
        chat_id = update.effective_chat.id
        status_msg = await update.message.reply_text("🔄 <i>Checking for newly released deals...</i>", parse_mode=ParseMode.HTML)

        sent_deal_ids = await self.db.get_sent_deal_ids_for_chat(chat_id)
        all_new_deals = await self.deal_manager.get_new_deals(sent_deal_ids)

        # Filter by user's enabled stores
        new_deals = [
            deal for deal in all_new_deals
            if await self.db.is_deal_allowed_for_user(chat_id, deal.store)
        ]

        if not new_deals:
            await status_msg.edit_text("✅ You are all caught up! No new free games matching your store preferences.")
            return

        await status_msg.edit_text(f"🎉 Found <b>{len(new_deals)}</b> new free game(s) for you!", parse_mode=ParseMode.HTML)

        for deal in new_deals:
            await send_deal_message(context.bot, chat_id, deal)
            await self.db.mark_deal_sent(deal.id, chat_id, deal.title, deal.store)

    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        await self.db.add_subscriber(
            chat_id=chat_id,
            username=user.username if user else None,
            first_name=user.first_name if user else None,
        )
        await update.message.reply_text(
            "🔔 <b>Subscribed!</b> You will automatically receive alerts whenever a new free game is available.\n"
            "Use /settings to choose your preferred stores!",
            parse_mode=ParseMode.HTML,
        )

    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unsubscribe command."""
        chat_id = update.effective_chat.id
        await self.db.remove_subscriber(chat_id)
        await update.message.reply_text(
            "🔕 <b>Unsubscribed.</b> You will no longer receive automated alerts. You can still use /free anytime!",
            parse_mode=ParseMode.HTML,
        )

    # --- Background Periodic Job ---

    async def periodic_check_job(self, context: ContextTypes.DEFAULT_TYPE):
        """Background job to check for new deals and notify active subscribers according to their store preferences."""
        logger.info("Running periodic free games check...")
        try:
            subscribers = await self.db.get_active_subscribers()
            if not subscribers:
                logger.info("No active subscribers to notify.")
                return

            all_deals = await self.deal_manager.fetch_all_deals(force_refresh=True)
            active_deals = [d for d in all_deals if not d.is_upcoming]

            for chat_id in subscribers:
                sent_ids = await self.db.get_sent_deal_ids_for_chat(chat_id)
                for deal in active_deals:
                    if deal.id not in sent_ids:
                        # Check store preference
                        if not await self.db.is_deal_allowed_for_user(chat_id, deal.store):
                            continue

                        logger.info(f"Broadcasting new deal '{deal.title}' ({deal.store}) to chat {chat_id}")
                        try:
                            await send_deal_message(context.bot, chat_id, deal)
                            await self.db.mark_deal_sent(deal.id, chat_id, deal.title, deal.store)
                        except Exception as e:
                            logger.error(f"Failed to send deal to subscriber {chat_id}: {e}")

        except Exception as e:
            logger.error(f"Error during periodic check job: {e}", exc_info=True)
