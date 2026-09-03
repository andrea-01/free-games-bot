"""Main entrypoint for Free Games Telegram Bot."""
import argparse
import asyncio
import logging
import sys
from free_games_bot.config import config
from free_games_bot.fetchers.manager import DealManager
from free_games_bot.formatter import format_deal_message
from free_games_bot.database import Database
from free_games_bot.bot import FreeGamesBot

def setup_logging():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, config.log_level, logging.INFO),
    )

async def test_fetch():
    """Fetch deals, enrich them, and display them in the terminal."""
    print("=" * 60)
    print("Testing Free Games Deal Fetcher & Metadata Enricher")
    print("=" * 60)

    manager = DealManager()
    deals = await manager.fetch_all_deals(force_refresh=True)

    print(f"\nFetched {len(deals)} total deals (including upcoming):")

    for i, deal in enumerate(deals, 1):
        caption, keyboard = format_deal_message(deal)
        print(f"\n--- [Deal #{i}] ---")
        print(f"Title:        {deal.clean_title()}")
        print(f"Store:        {deal.store}")
        print(f"Stock Price:  {deal.stock_price}")
        print(f"Store URL:    {deal.store_url}")
        print(f"Cover URL:    {deal.cover_url}")
        print(f"Year:         {deal.release_year or 'N/A'}")
        print(f"Genres:       {', '.join(deal.genres) if deal.genres else 'N/A'}")
        print(f"Player Modes: {', '.join(deal.player_modes) if deal.player_modes else 'N/A'}")
        print(f"Upcoming:     {deal.is_upcoming}")
        print(f"End Date:     {deal.end_date or 'N/A'}")
        print("\nTelegram Caption Preview:")
        print(caption)
        if keyboard and keyboard.inline_keyboard:
            btn = keyboard.inline_keyboard[0][0]
            print(f"Inline Button: [{btn.text}] -> {btn.url}")
        print("-" * 60)

    await manager.close()

def run_bot():
    """Start the Telegram bot with polling."""
    setup_logging()
    logger = logging.getLogger(__name__)

    if not config.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not configured. Please set it in .env or environment.")
        sys.exit(1)

    logger.info("Starting Free Games Telegram Bot...")

    bot_service = FreeGamesBot()
    # Initialize DB synchronously/async
    asyncio.run(bot_service.init())

    app = bot_service.build_application()
    logger.info("Bot application initialized. Starting polling...")
    app.run_polling()

def main():
    parser = argparse.ArgumentParser(description="Free Games Telegram Bot")
    parser.add_argument(
        "--test-fetch",
        action="store_true",
        help="Fetch active deals and display formatted previews in terminal without launching the bot",
    )
    args = parser.parse_args()

    if args.test_fetch:
        setup_logging()
        asyncio.run(test_fetch())
    else:
        run_bot()

if __name__ == "__main__":
    main()
