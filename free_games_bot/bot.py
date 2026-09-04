"""Telegram bot handlers, Italian localization, activity logging, and filtering by store, category, and price."""
import logging
from pathlib import Path
from typing import Optional, Set
from telegram import Update
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from telegram.error import TimedOut, NetworkError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from free_games_bot.config import config
from free_games_bot.database import Database, ALL_STORES, ALL_CATEGORIES
from free_games_bot.fetchers.manager import DealManager
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
)
from free_games_bot.models import GameDeal, extract_price_float, format_price_eur

logger = logging.getLogger(__name__)

async def send_deal_message(bot, chat_id: int, deal: GameDeal):
    """Invia un deal con la cover ad alta risoluzione, con fallback a messaggio di testo."""
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
            logger.warning(f"Impossibile inviare la foto ({deal.cover_url}) a {chat_id}: {e}. Invio messaggio di testo...")

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
        """Inizializza il database e i servizi interni."""
        await self.db.init_db()

    def build_application(self) -> Application:
        """Crea e configura l'applicazione Telegram con gestori e job queue."""
        if not config.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN non è impostato nelle variabili d'ambiente o nel file .env.")

        # Timeout resilienti per evitare disconnessioni o ritardi di rete
        request_config = HTTPXRequest(
            connect_timeout=15.0,
            read_timeout=25.0,
            write_timeout=25.0,
            pool_timeout=10.0,
        )
        builder = ApplicationBuilder().token(config.telegram_bot_token).request(request_config)
        app = builder.build()

        # Comandi utente
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler(["free", "giochi"], self.free_command))
        app.add_handler(CommandHandler("deals", self.deals_command))
        app.add_handler(CommandHandler(["nofilter_free", "nofilterfree", "allfree"], self.nofilter_free_command))
        # Supporta anche la variante con trattino /nofilter-free
        app.add_handler(MessageHandler(filters.Regex(r"^/nofilter-free(\s|$)"), self.nofilter_free_command))
        app.add_handler(CommandHandler("epic", self.epic_command))
        app.add_handler(CommandHandler("steam", self.steam_command))
        app.add_handler(CommandHandler("check", self.check_command))
        app.add_handler(CommandHandler(["settings", "impostazioni", "filtri"], self.settings_command))
        app.add_handler(CommandHandler("minprice", self.minprice_command))
        app.add_handler(CommandHandler("maxprice", self.maxprice_command))
        app.add_handler(CommandHandler("subscribe", self.subscribe_command))
        app.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))

        # Callback per menu interattivo
        app.add_handler(CallbackQueryHandler(self.settings_callback))

        # Gestore globale degli errori
        app.add_error_handler(self.error_handler)

        # Pianificazione controllo periodico in background
        if app.job_queue:
            interval_seconds = max(60, config.check_interval_minutes * 60)
            app.job_queue.run_repeating(
                self.periodic_check_job,
                interval=interval_seconds,
                first=10,
                name="periodic_deal_checker",
            )
            logger.info(f"Pianificato controllo automatico ogni {config.check_interval_minutes} minuti.")

        self.app = app
        return app

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Logga eventuali eccezioni non gestite."""
        if isinstance(context.error, (TimedOut, NetworkError)):
            logger.warning(f"[RETE TELEGRAM] Timeout o connessione lenta temporanea: {context.error}")
            return
        logger.error("Errore imprevisto durante la gestione di un aggiornamento:", exc_info=context.error)

    # --- Comandi Utente ---

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce il comando /start."""
        user = update.effective_user
        chat_id = update.effective_chat.id

        is_new = not await self.db.is_subscribed(chat_id)
        await self.db.add_subscriber(
            chat_id=chat_id,
            username=user.username if user else None,
            first_name=user.first_name if user else None,
        )

        user_tag = f"@{user.username}" if (user and user.username) else f"ID:{chat_id}"
        if is_new:
            logger.info(f"[NUOVO UTENTE] {user_tag} ({user.first_name if user else 'N/A'}) ha avviato il bot.")
        else:
            logger.info(f"[UTENTE COLLEGATO] {user_tag} ({user.first_name if user else 'N/A'}) ha riavviato /start.")

        welcome_text = (
            f"👋 <b>Benvenuto, {user.first_name if user else 'Gamer'}!</b>\n\n"
            "🎮 <b>Free Games Bot</b> monitora e ti segnala in tempo reale tutti i giochi gratuiti e le migliori offerte per PC!\n\n"
            "✨ <b>Funzionalità:</b>\n"
            "• Locandine ad alta risoluzione (SteamGridDB e store)\n"
            "• Prezzi e sconti ufficiali in <b>Euro (€)</b>\n"
            "• Dati completi (Anno, generi, singolo/multiplayer, recensioni)\n"
            "• Link diretti agli store in lingua italiana\n"
            "• Filtri avanzati per <b>Store</b>, <b>Categorie</b>, <b>Prezzi</b> e <b>Anti-Spam</b> (/settings)\n"
            "• Notifiche automatiche sui nuovi giochi gratis\n\n"
            "📌 <b>Comandi principali:</b>\n"
            "/free - Mostra i giochi 100% gratis secondo i tuoi filtri\n"
            "/deals - Mostra tutte le offerte (gratis e sconti) filtrate\n"
            "/nofilter_free - Tutti i giochi gratuiti disponibili senza filtri\n"
            "/settings - Configura store, generi, soglie di prezzo e qualità\n"
            "/epic & /steam - Promozioni per store\n"
            "/check - Cerca nuovi arrivi non ancora ricevuti\n"
            "/subscribe - Abilitati alle notifiche periodiche\n"
            "/help - Guida completa ai comandi"
        )
        if update.effective_message:
            banner_path = Path("assets/welcome_banner.jpg")
            if banner_path.exists():
                try:
                    with open(banner_path, "rb") as f:
                        await update.effective_message.reply_photo(
                            photo=f,
                            caption=welcome_text,
                            parse_mode=ParseMode.HTML,
                        )
                        return
                except Exception as e:
                    logger.warning(f"Impossibile inviare immagine di benvenuto: {e}")

            await update.effective_message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce il comando /help."""
        user = update.effective_user
        logger.info(f"[COMANDO /help] Utente: @{user.username if user else 'N/A'} ({update.effective_chat.id})")

        help_text = (
            "🛠 <b>Guida ai comandi di Free Games Bot:</b>\n\n"
            "/free - Mostra solo i titoli 100% gratuiti secondo i tuoi filtri\n"
            "/deals - Mostra l'elenco di tutte le offerte (gratis e sconti) filtrate\n"
            "/nofilter-free - Elenco di tutti i giochi gratuiti disponibili SENZA alcun filtro\n"
            "/settings - Apri il pannello filtri (Store, Categorie, Prezzi & Qualità)\n"
            "/minprice [euro] - Imposta il valore minimo del gioco (es. <code>/minprice 10</code> o <code>/minprice 0</code>)\n"
            "/maxprice [euro] - Imposta il prezzo max per offerte a pagamento (es. <code>/maxprice 5</code> o <code>/maxprice 0</code>)\n"
            "/epic - Visualizza le offerte attive e future di Epic Games Store\n"
            "/steam - Visualizza i giochi gratis e promozioni su Steam\n"
            "/check - Cerca subito nuovi giochi non ancora ricevuti\n"
            "/subscribe - Attiva le notifiche automatiche periodiche\n"
            "/unsubscribe - Disattiva le notifiche automatiche\n"
            "/help - Mostra questo messaggio di aiuto\n\n"
            "💡 <i>Tocca il pulsante sotto a ciascuna scheda per riscattare subito il gioco nello store italiano.</i>"
        )
        if update.effective_message:
            await update.effective_message.reply_text(help_text, parse_mode=ParseMode.HTML)

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce il comando /settings: apre il menu principale delle impostazioni."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        logger.info(f"[COMANDO /settings] Utente: @{user.username if user else 'N/A'} ({chat_id})")

        stores = await self.db.get_user_stores(chat_id)
        categories = await self.db.get_user_categories(chat_id)
        min_stock, max_sale = await self.db.get_user_prices(chat_id)
        ignore_free = await self.db.get_user_ignore_min_on_free(chat_id)
        min_rating, _ = await self.db.get_user_rating_filter(chat_id)

        text = format_main_settings_message(len(stores), len(categories), min_stock, max_sale, ignore_free, min_rating)
        keyboard = build_main_settings_keyboard()
        if update.effective_message:
            await update.effective_message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    async def minprice_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Imposta rapidamente la soglia di listino minimo via comando."""
        chat_id = update.effective_chat.id
        user = update.effective_user
        msg = update.effective_message
        if not msg:
            return

        if not context.args:
            min_stock, _ = await self.db.get_user_prices(chat_id)
            current_str = f"{min_stock:.2f}".replace(".", ",") + " €" if min_stock > 0 else "Nessun limite (0,00 €)"
            await msg.reply_text(
                f"💰 <b>Listino minimo attuale:</b> {current_str}\n\n"
                "Usa <code>/minprice [importo]</code> per cambiarlo (es. <code>/minprice 10</code>) o <code>/minprice 0</code> per azzerare.",
                parse_mode=ParseMode.HTML,
            )
            return

        arg = context.args[0]
        val = extract_price_float(arg)
        new_val = await self.db.set_user_min_stock_price(chat_id, val)
        logger.info(f"[IMPOSTAZIONI /minprice] Utente: @{user.username if user else 'N/A'} ({chat_id}) ha impostato min_stock a {new_val}€")

        if new_val <= 0:
            await msg.reply_text("✅ <b>Filtro listino minimo disattivato.</b> Riceverai giochi con qualsiasi valore originale.", parse_mode=ParseMode.HTML)
        else:
            formatted = f"{new_val:.2f}".replace(".", ",") + " €"
            await msg.reply_text(f"✅ <b>Listino minimo impostato a {formatted}.</b> Riceverai solo giochi con valore originale pari o superiore.", parse_mode=ParseMode.HTML)

    async def maxprice_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Imposta rapidamente la soglia massima per offerte scontate via comando."""
        chat_id = update.effective_chat.id
        user = update.effective_user
        msg = update.effective_message
        if not msg:
            return

        if not context.args:
            _, max_sale = await self.db.get_user_prices(chat_id)
            current_str = f"≤ {max_sale:.2f}".replace(".", ",") + " €" if max_sale > 0 else "Solo 100% GRATIS (0,00 €)"
            await msg.reply_text(
                f"💰 <b>Prezzo max offerta attuale:</b> {current_str}\n\n"
                "Usa <code>/maxprice [importo]</code> per cambiarlo (es. <code>/maxprice 5</code>) o <code>/maxprice 0</code> per soli giochi gratuiti.",
                parse_mode=ParseMode.HTML,
            )
            return

        arg = context.args[0]
        val = extract_price_float(arg)
        new_val = await self.db.set_user_max_sale_price(chat_id, val)
        logger.info(f"[IMPOSTAZIONI /maxprice] Utente: @{user.username if user else 'N/A'} ({chat_id}) ha impostato max_sale a {new_val}€")

        if new_val <= 0:
            await msg.reply_text("✅ <b>Filtro offerte impostato su SOLO GRATIS (0,00 €).</b>", parse_mode=ParseMode.HTML)
        else:
            formatted = f"{new_val:.2f}".replace(".", ",") + " €"
            await msg.reply_text(f"✅ <b>Filtro offerte impostato su ≤ {formatted}.</b> Riceverai sia giochi gratis sia sconti sotto questa soglia.", parse_mode=ParseMode.HTML)

    # --- Gestione Callback Impostazioni ---

    async def settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce tutti i pulsanti interattivi del menu /settings."""
        query = update.callback_query
        chat_id = query.message.chat.id
        user = query.from_user
        data = query.data

        if data == "noop":
            await query.answer()
            return

        logger.info(f"[CALLBACK] Utente: @{user.username if user else 'N/A'} ({chat_id}) ha premuto: {data}")
        await query.answer()

        # 1. Navigazione tra sezioni
        if data == "nav:main":
            stores = await self.db.get_user_stores(chat_id)
            categories = await self.db.get_user_categories(chat_id)
            min_stock, max_sale = await self.db.get_user_prices(chat_id)
            ignore_free = await self.db.get_user_ignore_min_on_free(chat_id)
            min_rating, _ = await self.db.get_user_rating_filter(chat_id)
            await query.edit_message_text(
                text=format_main_settings_message(len(stores), len(categories), min_stock, max_sale, ignore_free, min_rating),
                reply_markup=build_main_settings_keyboard(),
                parse_mode=ParseMode.HTML,
            )
            return

        if data == "nav:stores":
            stores = await self.db.get_user_stores(chat_id)
            await query.edit_message_text(
                text=format_stores_settings_message(stores),
                reply_markup=build_stores_keyboard(stores),
                parse_mode=ParseMode.HTML,
            )
            return

        if data == "nav:categories":
            categories = await self.db.get_user_categories(chat_id)
            await query.edit_message_text(
                text=format_categories_settings_message(categories),
                reply_markup=build_categories_keyboard(categories),
                parse_mode=ParseMode.HTML,
            )
            return

        if data == "nav:prices":
            min_stock, max_sale = await self.db.get_user_prices(chat_id)
            ignore_free = await self.db.get_user_ignore_min_on_free(chat_id)
            min_rating, _ = await self.db.get_user_rating_filter(chat_id)
            await query.edit_message_text(
                text=format_prices_settings_message(min_stock, max_sale, ignore_free, min_rating),
                reply_markup=build_prices_keyboard(min_stock, max_sale, ignore_free, min_rating),
                parse_mode=ParseMode.HTML,
            )
            return

        if data == "nav:close":
            await query.message.delete()
            return

        # 2. Toggle Store
        if data.startswith("toggle_store:"):
            store = data.split(":", 1)[1]
            stores = await self.db.toggle_user_store(chat_id, store)
            await query.edit_message_text(
                text=format_stores_settings_message(stores),
                reply_markup=build_stores_keyboard(stores),
                parse_mode=ParseMode.HTML,
            )
            return

        if data == "preset_store:all":
            stores = await self.db.set_user_stores(chat_id, set(ALL_STORES))
            await query.edit_message_text(
                text=format_stores_settings_message(stores),
                reply_markup=build_stores_keyboard(stores),
                parse_mode=ParseMode.HTML,
            )
            return

        if data == "preset_store:none":
            stores = await self.db.set_user_stores(chat_id, set())
            await query.edit_message_text(
                text=format_stores_settings_message(stores),
                reply_markup=build_stores_keyboard(stores),
                parse_mode=ParseMode.HTML,
            )
            return

        # 3. Toggle Categorie
        if data.startswith("toggle_cat:"):
            cat = data.split(":", 1)[1]
            categories = await self.db.toggle_user_category(chat_id, cat)
            await query.edit_message_text(
                text=format_categories_settings_message(categories),
                reply_markup=build_categories_keyboard(categories),
                parse_mode=ParseMode.HTML,
            )
            return

        if data == "preset_cat:all":
            categories = await self.db.set_user_categories(chat_id, set(ALL_CATEGORIES))
            await query.edit_message_text(
                text=format_categories_settings_message(categories),
                reply_markup=build_categories_keyboard(categories),
                parse_mode=ParseMode.HTML,
            )
            return

        if data == "preset_cat:none":
            categories = await self.db.set_user_categories(chat_id, set())
            await query.edit_message_text(
                text=format_categories_settings_message(categories),
                reply_markup=build_categories_keyboard(categories),
                parse_mode=ParseMode.HTML,
            )
            return

        # 4. Impostazioni Prezzi & Qualità
        if data == "toggle_ignore_min_free":
            await self.db.toggle_user_ignore_min_on_free(chat_id)
            min_stock, max_sale = await self.db.get_user_prices(chat_id)
            ignore_free = await self.db.get_user_ignore_min_on_free(chat_id)
            min_rating, _ = await self.db.get_user_rating_filter(chat_id)
            await query.edit_message_text(
                text=format_prices_settings_message(min_stock, max_sale, ignore_free, min_rating),
                reply_markup=build_prices_keyboard(min_stock, max_sale, ignore_free, min_rating),
                parse_mode=ParseMode.HTML,
            )
            return

        if data.startswith("set_min_rating:"):
            val = int(data.split(":", 1)[1])
            min_reviews = 10 if val > 0 else 0
            await self.db.set_user_rating_filter(chat_id, val, min_reviews)
            min_stock, max_sale = await self.db.get_user_prices(chat_id)
            ignore_free = await self.db.get_user_ignore_min_on_free(chat_id)
            min_rating, _ = await self.db.get_user_rating_filter(chat_id)
            await query.edit_message_text(
                text=format_prices_settings_message(min_stock, max_sale, ignore_free, min_rating),
                reply_markup=build_prices_keyboard(min_stock, max_sale, ignore_free, min_rating),
                parse_mode=ParseMode.HTML,
            )
            return

        if data.startswith("set_min:"):
            val = float(data.split(":", 1)[1])
            await self.db.set_user_min_stock_price(chat_id, val)
            min_stock, max_sale = await self.db.get_user_prices(chat_id)
            ignore_free = await self.db.get_user_ignore_min_on_free(chat_id)
            min_rating, _ = await self.db.get_user_rating_filter(chat_id)
            await query.edit_message_text(
                text=format_prices_settings_message(min_stock, max_sale, ignore_free, min_rating),
                reply_markup=build_prices_keyboard(min_stock, max_sale, ignore_free, min_rating),
                parse_mode=ParseMode.HTML,
            )
            return

        if data.startswith("set_max:"):
            val = float(data.split(":", 1)[1])
            await self.db.set_user_max_sale_price(chat_id, val)
            min_stock, max_sale = await self.db.get_user_prices(chat_id)
            ignore_free = await self.db.get_user_ignore_min_on_free(chat_id)
            min_rating, _ = await self.db.get_user_rating_filter(chat_id)
            await query.edit_message_text(
                text=format_prices_settings_message(min_stock, max_sale, ignore_free, min_rating),
                reply_markup=build_prices_keyboard(min_stock, max_sale, ignore_free, min_rating),
                parse_mode=ParseMode.HTML,
            )
            return

        if data == "reset_prices":
            await self.db.reset_user_prices(chat_id)
            await query.edit_message_text(
                text=format_prices_settings_message(0.0, 0.0, True, 0),
                reply_markup=build_prices_keyboard(0.0, 0.0, True, 0),
                parse_mode=ParseMode.HTML,
            )
            return

    # --- Comandi Ricerca & Offerte con Filtri ---

    async def free_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce /free: mostra solo i titoli attualmente GRATUITI (100% sconto) secondo i filtri dell'utente."""
        chat_id = update.effective_chat.id
        user = update.effective_user
        logger.info(f"[COMANDO /free] Utente: @{user.username if user else 'N/A'} ({chat_id})")

        msg = update.effective_message
        if not msg:
            return
        status_msg = await msg.reply_text("🔍 <i>Ricerca giochi gratuiti attivi...</i>", parse_mode=ParseMode.HTML)

        min_stock, _ = await self.db.get_user_prices(chat_id)
        all_deals = await self.deal_manager.fetch_all_deals(
            max_sale_price=0.0,
            min_stock_price=min_stock,
        )

        active_free = [d for d in all_deals if not d.is_upcoming and d.sale_price_value <= 0.01]

        filtered_deals = []
        for d in active_free:
            if not await self.db.is_deal_allowed_for_user(chat_id, d.store):
                continue
            if not await self.db.is_deal_category_allowed(chat_id, d.genres):
                continue
            if not await self.db.is_deal_price_allowed(chat_id, d.stock_price_value, d.sale_price_value):
                continue
            if not await self.db.is_deal_quality_allowed(chat_id, d.rating_percent, d.reviews_count, d.store):
                continue
            filtered_deals.append(d)

        if not filtered_deals:
            await status_msg.edit_text(
                "ℹ️ Nessun gioco 100% gratuito trovato che corrisponda ai tuoi filtri attuali!\n"
                "Usa /settings per modificare store, generi o soglie, oppure usa /nofilter-free per vedere tutti i giochi gratis disponibili senza alcun filtro."
            )
            return

        await status_msg.edit_text(f"🎁 Trovati <b>{len(filtered_deals)}</b> giochi 100% gratuiti per te! Invio in corso...", parse_mode=ParseMode.HTML)

        for deal in filtered_deals:
            await send_deal_message(context.bot, chat_id, deal)
            await self.db.mark_deal_sent(deal.id, chat_id, deal.title, deal.store)

    async def deals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce /deals: fornisce l'elenco di tutte le offerte (gratis e sconti) corrispondenti ai filtri."""
        chat_id = update.effective_chat.id
        user = update.effective_user
        logger.info(f"[COMANDO /deals] Utente: @{user.username if user else 'N/A'} ({chat_id})")

        msg = update.effective_message
        if not msg:
            return
        status_msg = await msg.reply_text("🔍 <i>Ricerca offerte e promozioni secondo i tuoi filtri...</i>", parse_mode=ParseMode.HTML)

        min_stock, max_sale = await self.db.get_user_prices(chat_id)
        all_deals = await self.deal_manager.fetch_all_deals(
            max_sale_price=max_sale,
            min_stock_price=min_stock,
        )

        active_deals = [d for d in all_deals if not d.is_upcoming]

        filtered_deals = []
        for d in active_deals:
            if not await self.db.is_deal_allowed_for_user(chat_id, d.store):
                continue
            if not await self.db.is_deal_category_allowed(chat_id, d.genres):
                continue
            if not await self.db.is_deal_price_allowed(chat_id, d.stock_price_value, d.sale_price_value):
                continue
            if not await self.db.is_deal_quality_allowed(chat_id, d.rating_percent, d.reviews_count, d.store):
                continue
            filtered_deals.append(d)

        if not filtered_deals:
            await status_msg.edit_text(
                "ℹ️ Nessuna offerta trovata che corrisponda ai tuoi filtri attuali!\n"
                "Usa /settings per modificare store, generi o aumentare il prezzo massimo dell'offerta."
            )
            return

        await status_msg.edit_text(f"🔥 Trovate <b>{len(filtered_deals)}</b> offerte per te! Invio in corso...", parse_mode=ParseMode.HTML)

        for deal in filtered_deals:
            await send_deal_message(context.bot, chat_id, deal)
            await self.db.mark_deal_sent(deal.id, chat_id, deal.title, deal.store)

    async def nofilter_free_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce /nofilter-free: elenco di tutti i giochi gratuiti disponibili senza alcun filtro."""
        chat_id = update.effective_chat.id
        user = update.effective_user
        logger.info(f"[COMANDO /nofilter-free] Utente: @{user.username if user else 'N/A'} ({chat_id})")

        msg = update.effective_message
        if not msg:
            return
        status_msg = await msg.reply_text("🔍 <i>Recupero di TUTTI i giochi gratuiti disponibili senza filtri...</i>", parse_mode=ParseMode.HTML)

        all_deals = await self.deal_manager.fetch_all_deals(
            max_sale_price=0.0,
            min_stock_price=0.0,
        )

        # Solo giochi attualmente gratuiti (senza filtri di store, categorie, listino o qualità)
        active_free = [d for d in all_deals if not d.is_upcoming and d.sale_price_value <= 0.01]

        if not active_free:
            await status_msg.edit_text("ℹ️ Nessun gioco gratuito disponibile al 100% in questo momento su nessuno store.")
            return

        await status_msg.edit_text(f"🎁 Trovati <b>{len(active_free)}</b> giochi gratuiti totali senza filtri! Invio in corso...", parse_mode=ParseMode.HTML)

        for deal in active_free:
            await send_deal_message(context.bot, chat_id, deal)
            await self.db.mark_deal_sent(deal.id, chat_id, deal.title, deal.store)

    async def epic_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce /epic."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        logger.info(f"[COMANDO /epic] Utente: @{user.username if user else 'N/A'} ({chat_id})")

        msg = update.effective_message
        if not msg:
            return
        status_msg = await msg.reply_text("🔍 <i>Recupero promozioni di Epic Games Store...</i>", parse_mode=ParseMode.HTML)
        deals = await self.deal_manager.get_epic_deals()

        if not deals:
            await status_msg.edit_text("ℹ️ Nessuna promozione attiva trovata su Epic Games al momento.")
            return

        await status_msg.edit_text(f"🎁 Trovate <b>{len(deals)}</b> promozioni Epic Games (attive & future):", parse_mode=ParseMode.HTML)
        for deal in deals:
            await send_deal_message(context.bot, chat_id, deal)
            await self.db.mark_deal_sent(deal.id, chat_id, deal.title, deal.store)

    async def steam_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce /steam."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        logger.info(f"[COMANDO /steam] Utente: @{user.username if user else 'N/A'} ({chat_id})")

        msg = update.effective_message
        if not msg:
            return
        status_msg = await msg.reply_text("🔍 <i>Recupero promozioni Steam...</i>", parse_mode=ParseMode.HTML)
        deals = await self.deal_manager.get_steam_deals()

        if not deals:
            await status_msg.edit_text("ℹ️ Nessuna promozione al 100% trovata su Steam in questo momento.")
            return

        await status_msg.edit_text(f"🎁 Trovate <b>{len(deals)}</b> promozioni Steam:", parse_mode=ParseMode.HTML)
        for deal in deals:
            await send_deal_message(context.bot, chat_id, deal)
            await self.db.mark_deal_sent(deal.id, chat_id, deal.title, deal.store)

    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce /check: scansiona i deal non ancora inviati all'utente applicando tutti i filtri."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        logger.info(f"[COMANDO /check] Utente: @{user.username if user else 'N/A'} ({chat_id})")

        msg = update.effective_message
        if not msg:
            return
        status_msg = await msg.reply_text("🔄 <i>Controllo nuovi arrivi non ancora ricevuti...</i>", parse_mode=ParseMode.HTML)

        min_stock, max_sale = await self.db.get_user_prices(chat_id)
        sent_deal_ids = await self.db.get_sent_deal_ids_for_chat(chat_id)
        all_new_deals = await self.deal_manager.get_new_deals(sent_deal_ids, max_sale_price=max_sale, min_stock_price=min_stock)

        filtered_deals = []
        for d in all_new_deals:
            if not await self.db.is_deal_allowed_for_user(chat_id, d.store):
                continue
            if not await self.db.is_deal_category_allowed(chat_id, d.genres):
                continue
            if not await self.db.is_deal_price_allowed(chat_id, d.stock_price_value, d.sale_price_value):
                continue
            if not await self.db.is_deal_quality_allowed(chat_id, d.rating_percent, d.reviews_count, d.store):
                continue
            filtered_deals.append(d)

        if not filtered_deals:
            await status_msg.edit_text("✅ Nessun nuovo gioco rispetto al tuo ultimo controllo! Sei aggiornato.")
            return

        await status_msg.edit_text(f"🎉 Trovati <b>{len(filtered_deals)}</b> nuovi giochi per te!", parse_mode=ParseMode.HTML)
        for deal in filtered_deals:
            await send_deal_message(context.bot, chat_id, deal)
            await self.db.mark_deal_sent(deal.id, chat_id, deal.title, deal.store)

    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce /subscribe."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        logger.info(f"[COMANDO /subscribe] Utente: @{user.username if user else 'N/A'} ({chat_id})")

        await self.db.add_subscriber(
            chat_id=chat_id,
            username=user.username if user else None,
            first_name=user.first_name if user else None,
        )
        if update.effective_message:
            await update.effective_message.reply_text(
                "🔔 <b>Notifiche attive!</b> Riceverai avvisi automatici quando un nuovo gioco gratuito è disponibile.\n"
                "Puoi personalizzare store, categorie e prezzi con /settings.",
                parse_mode=ParseMode.HTML,
            )

    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestisce /unsubscribe."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        logger.info(f"[COMANDO /unsubscribe] Utente: @{user.username if user else 'N/A'} ({chat_id})")

        await self.db.remove_subscriber(chat_id)
        if update.effective_message:
            await update.effective_message.reply_text(
                "🔕 <b>Notifiche disattivate.</b> Non riceverai più notifiche automatiche. Potrai comunque consultare /free quando vuoi!",
                parse_mode=ParseMode.HTML,
            )

    # --- Job Periodico in Background ---

    async def periodic_check_job(self, context: ContextTypes.DEFAULT_TYPE):
        """Controllo periodico in background con invio deal personalizzato per ogni utente."""
        logger.info("[BACKGROUND] Avvio controllo periodico offerte e giochi gratis...")
        try:
            subscribers = await self.db.get_active_subscribers()
            if not subscribers:
                logger.info("[BACKGROUND] Nessun utente attivo iscritto alle notifiche.")
                return

            all_deals = await self.deal_manager.fetch_all_deals(force_refresh=True)
            active_deals = [d for d in all_deals if not d.is_upcoming]

            for chat_id in subscribers:
                sent_ids = await self.db.get_sent_deal_ids_for_chat(chat_id)
                for deal in active_deals:
                    if deal.id not in sent_ids:
                        if not await self.db.is_deal_allowed_for_user(chat_id, deal.store):
                            continue
                        if not await self.db.is_deal_category_allowed(chat_id, deal.genres):
                            continue
                        if not await self.db.is_deal_price_allowed(chat_id, deal.stock_price_value, deal.sale_price_value):
                            continue
                        if not await self.db.is_deal_quality_allowed(chat_id, deal.rating_percent, deal.reviews_count, deal.store):
                            continue

                        logger.info(f"[NOTIFICA DEAL] Invio '{deal.title}' ({deal.store}, {deal.stock_price}) a chat {chat_id}")
                        try:
                            await send_deal_message(context.bot, chat_id, deal)
                            await self.db.mark_deal_sent(deal.id, chat_id, deal.title, deal.store)
                        except Exception as e:
                            logger.error(f"Errore durante l'invio del deal a {chat_id}: {e}")

        except Exception as e:
            logger.error(f"Errore durante il controllo periodico: {e}", exc_info=True)
