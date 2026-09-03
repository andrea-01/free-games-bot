"""Unit tests for SQLite database operations."""
import os
import pytest
from free_games_bot.database import Database, ALL_STORES, normalize_deal_store

@pytest.mark.asyncio
async def test_database_subscribers(tmp_path):
    db_file = str(tmp_path / "test.db")
    db = Database(db_path=db_file)
    await db.init_db()

    # Initial subscribers should be empty
    subs = await db.get_active_subscribers()
    assert len(subs) == 0

    # Add subscriber
    await db.add_subscriber(chat_id=12345, username="testuser", first_name="Test")
    assert await db.is_subscribed(12345) is True

    subs = await db.get_active_subscribers()
    assert subs == [12345]

    # Remove subscriber
    await db.remove_subscriber(12345)
    assert await db.is_subscribed(12345) is False
    assert await db.get_active_subscribers() == []

@pytest.mark.asyncio
async def test_database_sent_deals(tmp_path):
    db_file = str(tmp_path / "test.db")
    db = Database(db_path=db_file)
    await db.init_db()

    # Deal not sent initially
    assert await db.is_deal_sent("deal_abc", 12345) is False

    # Mark as sent
    await db.mark_deal_sent("deal_abc", 12345, title="Test Game", store="Steam")
    assert await db.is_deal_sent("deal_abc", 12345) is True

    sent_set = await db.get_sent_deal_ids_for_chat(12345)
    assert "deal_abc" in sent_set

    # Different chat should not have this deal marked
    assert await db.is_deal_sent("deal_abc", 99999) is False

@pytest.mark.asyncio
async def test_database_store_preferences(tmp_path):
    db_file = str(tmp_path / "test.db")
    db = Database(db_path=db_file)
    await db.init_db()

    await db.add_subscriber(chat_id=12345)

    # Defaults to all stores enabled
    stores = await db.get_user_stores(12345)
    assert len(stores) == len(ALL_STORES)
    assert "Epic Games" in stores
    assert "Steam" in stores

    # Deal allowed check
    assert await db.is_deal_allowed_for_user(12345, "Epic Games") is True
    assert await db.is_deal_allowed_for_user(12345, "Steam") is True

    # Toggle Steam off
    new_stores = await db.toggle_user_store(12345, "Steam")
    assert "Steam" not in new_stores
    assert await db.is_deal_allowed_for_user(12345, "Steam") is False
    assert await db.is_deal_allowed_for_user(12345, "Epic Games") is True

    # Toggle Steam back on
    new_stores2 = await db.toggle_user_store(12345, "Steam")
    assert "Steam" in new_stores2
    assert await db.is_deal_allowed_for_user(12345, "Steam") is True

def test_normalize_deal_store():
    assert normalize_deal_store("Epic Games") == "Epic Games"
    assert normalize_deal_store("Steam") == "Steam"
    assert normalize_deal_store("Itch.io") == "Itch.io"
    assert normalize_deal_store("Ubisoft Connect") == "Ubisoft"
    assert normalize_deal_store("EA App") == "EA / Origin"
    assert normalize_deal_store("Random DRM-Free Site") == "Other / DRM-Free"
