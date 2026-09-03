"""Database management for subscribers, store preferences, and sent deals."""
import json
import logging
import aiosqlite
from pathlib import Path
from typing import List, Set, Optional
from free_games_bot.config import config

logger = logging.getLogger(__name__)

ALL_STORES = [
    "Epic Games",
    "Steam",
    "GOG",
    "Ubisoft",
    "EA / Origin",
    "Itch.io",
    "Other / DRM-Free",
]

def normalize_deal_store(deal_store: str) -> str:
    """Map any deal store string to one of the canonical ALL_STORES options."""
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
    return "Other / DRM-Free"

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

            # Migration: add enabled_stores column if upgrading an existing db
            try:
                await db.execute("ALTER TABLE subscribers ADD COLUMN enabled_stores TEXT;")
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

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE subscribers SET enabled_stores = ? WHERE chat_id = ?;
            """, (json.dumps(list(current_stores)), chat_id))
            await db.commit()

        return current_stores

    async def is_deal_allowed_for_user(self, chat_id: int, deal_store: str) -> bool:
        """Check if the given deal's store is enabled by the user."""
        user_stores = await self.get_user_stores(chat_id)
        canonical = normalize_deal_store(deal_store)
        return canonical in user_stores

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
