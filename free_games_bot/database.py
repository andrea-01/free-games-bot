"""Database management for subscribers, preferences (stores, categories, prices), and sent deals."""
import json
import logging
import aiosqlite
from pathlib import Path
from typing import List, Set, Tuple, Optional
from free_games_bot.config import config
from free_games_bot.models import extract_price_float

logger = logging.getLogger(__name__)

ALL_STORES = [
    "Epic Games",
    "Steam",
    "GOG",
    "Ubisoft",
    "EA / Origin",
    "Itch.io",
    "Altro / DRM-Free",
]

ALL_CATEGORIES = [
    "Azione",
    "Avventura",
    "GDR / RPG",
    "Strategia",
    "Sparatutto",
    "Puzzle",
    "Simulazione",
    "Indie",
    "Horror",
    "Altro",
]

def normalize_deal_store(deal_store: str) -> str:
    """Map any store string to canonical ALL_STORES options."""
    s = deal_store.lower()
    if "epic" in s:
        return "Epic Games"
    if "steam" in s:
        return "Steam"
    if "gog" in s:
        return "GOG"
    if "ubisoft" in s or "uplay" in s:
        return "Ubisoft"
    if "ea" in s or "origin" in s:
        return "EA / Origin"
    if "itch" in s:
        return "Itch.io"
    return "Altro / DRM-Free"

def normalize_deal_category(genre: str) -> str:
    """Map an arbitrary genre/category string to one of ALL_CATEGORIES."""
    g = genre.lower()
    if "sparatutto" in g or "shooter" in g or "fps" in g:
        return "Sparatutto"
    if "rpg" in g or "ruolo" in g or "gdr" in g:
        return "GDR / RPG"
    if "azione" in g or "action" in g:
        return "Azione"
    if "avventura" in g or "adventure" in g:
        return "Avventura"
    if "strategia" in g or "strategy" in g or "rts" in g:
        return "Strategia"
    if "puzzle" in g or "rompicapo" in g or "enigmi" in g:
        return "Puzzle"
    if "simulazione" in g or "simulation" in g or "sim" in g:
        return "Simulazione"
    if "horror" in g or "sopravvivenza" in g or "survival" in g:
        return "Horror"
    if "indie" in g:
        return "Indie"
    return "Altro"

class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database_path

    async def init_db(self):
        """Initialize database schema, tables, and migrations."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    chat_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    is_active INTEGER DEFAULT 1,
                    enabled_stores TEXT,
                    enabled_categories TEXT,
                    min_stock_price REAL DEFAULT 0.0,
                    max_sale_price REAL DEFAULT 0.0,
                    ignore_min_on_free INTEGER DEFAULT 1,
                    min_rating INTEGER DEFAULT 0,
                    min_reviews INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sent_deals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    deal_id TEXT NOT NULL,
                    chat_id INTEGER NOT NULL,
                    title TEXT,
                    store TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(deal_id, chat_id)
                );
            """)

            # Migrations for existing databases
            columns_to_add = [
                ("enabled_stores", "TEXT"),
                ("enabled_categories", "TEXT"),
                ("min_stock_price", "REAL DEFAULT 0.0"),
                ("max_sale_price", "REAL DEFAULT 0.0"),
                ("ignore_min_on_free", "INTEGER DEFAULT 1"),
                ("min_rating", "INTEGER DEFAULT 0"),
                ("min_reviews", "INTEGER DEFAULT 0"),
            ]
            for col_name, col_type in columns_to_add:
                try:
                    await db.execute(f"ALTER TABLE subscribers ADD COLUMN {col_name} {col_type};")
                except Exception:
                    pass  # Column already exists

            await db.commit()

    async def add_subscriber(self, chat_id: int, username: str = None, first_name: str = None) -> bool:
        """Register or re-activate a subscriber."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO subscribers (chat_id, username, first_name, is_active)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(chat_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    is_active = 1;
            """, (chat_id, username, first_name))
            await db.commit()
            return True

    async def remove_subscriber(self, chat_id: int) -> bool:
        """Deactivate a subscriber."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE subscribers SET is_active = 0 WHERE chat_id = ?;
            """, (chat_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def is_subscribed(self, chat_id: int) -> bool:
        """Check if chat_id is an active subscriber."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT is_active FROM subscribers WHERE chat_id = ?;", (chat_id,)) as cursor:
                row = await cursor.fetchone()
                return bool(row and row[0] == 1)

    async def get_active_subscribers(self) -> List[int]:
        """Return list of all active subscriber chat IDs."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT chat_id FROM subscribers WHERE is_active = 1;") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    # --- Store Preferences ---

    async def get_user_stores(self, chat_id: int) -> Set[str]:
        """Get enabled stores for a user. Defaults to ALL_STORES if none configured."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT enabled_stores FROM subscribers WHERE chat_id = ?;", (chat_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    try:
                        stores = json.loads(row[0])
                        return set(stores)
                    except Exception:
                        pass
        return set(ALL_STORES)

    async def toggle_user_store(self, chat_id: int, store: str) -> Set[str]:
        """Toggle a specific store on/off for a user."""
        current_stores = await self.get_user_stores(chat_id)
        if store in current_stores:
            current_stores.remove(store)
        else:
            current_stores.add(store)
        await self.set_user_stores(chat_id, current_stores)
        return current_stores

    async def set_user_stores(self, chat_id: int, stores: Set[str]) -> Set[str]:
        """Set enabled stores for a user directly."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE subscribers SET enabled_stores = ? WHERE chat_id = ?;
            """, (json.dumps(list(stores)), chat_id))
            await db.commit()
        return stores

    async def is_deal_allowed_for_user(self, chat_id: int, deal_store: str) -> bool:
        """Check if the given deal's store is enabled by the user."""
        user_stores = await self.get_user_stores(chat_id)
        canonical = normalize_deal_store(deal_store)
        return canonical in user_stores

    # --- Category Preferences ---

    async def get_user_categories(self, chat_id: int) -> Set[str]:
        """Get enabled categories for a user. Defaults to ALL_CATEGORIES."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT enabled_categories FROM subscribers WHERE chat_id = ?;", (chat_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0]:
                    try:
                        categories = json.loads(row[0])
                        return set(categories)
                    except Exception:
                        pass
        return set(ALL_CATEGORIES)

    async def toggle_user_category(self, chat_id: int, category: str) -> Set[str]:
        """Toggle a specific category on/off for a user."""
        current = await self.get_user_categories(chat_id)
        if category in current:
            current.remove(category)
        else:
            current.add(category)
        await self.set_user_categories(chat_id, current)
        return current

    async def set_user_categories(self, chat_id: int, categories: Set[str]) -> Set[str]:
        """Set enabled categories directly."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE subscribers SET enabled_categories = ? WHERE chat_id = ?;
            """, (json.dumps(list(categories)), chat_id))
            await db.commit()
        return categories

    async def is_deal_category_allowed(self, chat_id: int, deal_genres: List[str]) -> bool:
        """Check if deal matches the user's enabled categories."""
        user_categories = await self.get_user_categories(chat_id)
        if not deal_genres:
            return "Altro" in user_categories

        # If any of the deal's genres map to an enabled user category
        for g in deal_genres:
            cat = normalize_deal_category(g)
            if cat in user_categories:
                return True
        return False

    # --- Price Filter Preferences ---

    async def get_user_prices(self, chat_id: int) -> Tuple[float, float]:
        """Get (min_stock_price, max_sale_price) for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT min_stock_price, max_sale_price FROM subscribers WHERE chat_id = ?;", (chat_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    min_stock = float(row[0] or 0.0)
                    max_sale = float(row[1] or 0.0)
                    return min_stock, max_sale
        return 0.0, 0.0

    async def set_user_min_stock_price(self, chat_id: int, min_price: float) -> float:
        """Set minimum stock price threshold (0 means no limit)."""
        val = max(0.0, round(min_price, 2))
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE subscribers SET min_stock_price = ? WHERE chat_id = ?;", (val, chat_id))
            await db.commit()
        return val

    async def set_user_max_sale_price(self, chat_id: int, max_price: float) -> float:
        """Set maximum discounted sale price threshold (0 means free only)."""
        val = max(0.0, round(max_price, 2))
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE subscribers SET max_sale_price = ? WHERE chat_id = ?;", (val, chat_id))
            await db.commit()
        return val

    async def get_user_ignore_min_on_free(self, chat_id: int) -> bool:
        """Check if user wants to bypass min_stock_price for 100% free games. Defaults to True."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT ignore_min_on_free FROM subscribers WHERE chat_id = ?;", (chat_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0] is not None:
                    return bool(row[0] == 1)
        return True

    async def toggle_user_ignore_min_on_free(self, chat_id: int) -> bool:
        """Toggle ignore_min_on_free setting."""
        current = await self.get_user_ignore_min_on_free(chat_id)
        new_val = not current
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE subscribers SET ignore_min_on_free = ? WHERE chat_id = ?;", (1 if new_val else 0, chat_id)
            )
            await db.commit()
        return new_val

    # --- Quality & Rating Filters ---

    async def get_user_rating_filter(self, chat_id: int) -> Tuple[int, int]:
        """Get (min_rating_percent, min_reviews) for a user. Defaults to (0, 0)."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT min_rating, min_reviews FROM subscribers WHERE chat_id = ?;", (chat_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    min_rating = int(row[0] or 0)
                    min_reviews = int(row[1] or 0)
                    return min_rating, min_reviews
        return 0, 0

    async def set_user_rating_filter(self, chat_id: int, min_rating: int, min_reviews: int = 0):
        """Set minimum review score percentage and minimum review count."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE subscribers SET min_rating = ?, min_reviews = ? WHERE chat_id = ?;",
                (max(0, min_rating), max(0, min_reviews), chat_id),
            )
            await db.commit()

    async def reset_user_prices(self, chat_id: int):
        """Reset price and rating filters to default."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE subscribers
                SET min_stock_price = 0.0, max_sale_price = 0.0, ignore_min_on_free = 1, min_rating = 0, min_reviews = 0
                WHERE chat_id = ?;
            """, (chat_id,))
            await db.commit()

    async def is_deal_price_allowed(self, chat_id: int, stock_price_val: float, sale_price_val: float) -> bool:
        """Check if deal satisfies min stock price, max sale price, and free bypass rules."""
        min_stock, max_sale = await self.get_user_prices(chat_id)
        ignore_on_free = await self.get_user_ignore_min_on_free(chat_id)

        is_free = sale_price_val <= 0.01

        # 1. Min stock price filter
        if min_stock > 0:
            if is_free and ignore_on_free:
                # User chose to keep 100% free games regardless of retail price
                pass
            elif stock_price_val < min_stock:
                return False

        # 2. Max sale price filter
        if max_sale > 0:
            if sale_price_val > max_sale:
                return False
        else:
            # If max_sale == 0.0, deal must be completely free (sale_price <= 0.01)
            if not is_free:
                return False

        return True

    async def is_deal_quality_allowed(
        self,
        chat_id: int,
        rating_percent: Optional[int],
        reviews_count: Optional[int],
        store: str = ""
    ) -> bool:
        """Check if deal satisfies user's minimum quality/rating criteria."""
        min_rating, min_reviews = await self.get_user_rating_filter(chat_id)
        if min_rating <= 0 and min_reviews <= 0:
            return True

        # Curated giveaway stores (Epic Games, Prime Gaming, GOG) are allowed through if unrated
        curated_stores = {"Epic Games", "Prime Gaming", "GOG"}
        if rating_percent is None and store in curated_stores:
            return True

        # If rating is known, check against thresholds
        if rating_percent is not None:
            if rating_percent < min_rating:
                return False
            if min_reviews > 0 and (reviews_count or 0) < min_reviews:
                return False
            return True

        # If unrated on open stores (Steam, Itch, etc.) and quality filter is active, exclude it
        return False

    # --- Sent Deals Tracking ---

    async def is_deal_sent(self, deal_id: str, chat_id: int) -> bool:
        """Check if a deal was already sent to this chat."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM sent_deals WHERE deal_id = ? AND chat_id = ?;", (deal_id, chat_id)) as cursor:
                row = await cursor.fetchone()
                return row is not None

    async def mark_deal_sent(self, deal_id: str, chat_id: int, title: str = "", store: str = ""):
        """Record that a deal has been dispatched to a chat."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO sent_deals (deal_id, chat_id, title, store)
                VALUES (?, ?, ?, ?);
            """, (deal_id, chat_id, title, store))
            await db.commit()

    async def get_sent_deal_ids_for_chat(self, chat_id: int) -> Set[str]:
        """Get set of deal IDs sent to a chat."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT deal_id FROM sent_deals WHERE chat_id = ?;", (chat_id,)) as cursor:
                rows = await cursor.fetchall()
                return {row[0] for row in rows}
