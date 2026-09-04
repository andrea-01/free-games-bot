"""Unit tests for SQLite database operations, stores, categories, and price preferences."""
import os
import pytest
from free_games_bot.database import Database, ALL_STORES, ALL_CATEGORIES, normalize_deal_store, normalize_deal_category

@pytest.mark.asyncio
async def test_database_subscribers(tmp_path):
    db_file = str(tmp_path / "test.db")
    db = Database(db_path=db_file)
    await db.init_db()

    subs = await db.get_active_subscribers()
    assert len(subs) == 0

    await db.add_subscriber(chat_id=12345, username="testuser", first_name="Test")
    assert await db.is_subscribed(12345) is True

    subs = await db.get_active_subscribers()
    assert subs == [12345]

    await db.remove_subscriber(12345)
    assert await db.is_subscribed(12345) is False
    assert await db.get_active_subscribers() == []

@pytest.mark.asyncio
async def test_database_sent_deals(tmp_path):
    db_file = str(tmp_path / "test.db")
    db = Database(db_path=db_file)
    await db.init_db()

    assert await db.is_deal_sent("deal_abc", 12345) is False
    await db.mark_deal_sent("deal_abc", 12345, title="Test Game", store="Steam")
    assert await db.is_deal_sent("deal_abc", 12345) is True

    sent_set = await db.get_sent_deal_ids_for_chat(12345)
    assert "deal_abc" in sent_set

@pytest.mark.asyncio
async def test_database_store_preferences(tmp_path):
    db_file = str(tmp_path / "test.db")
    db = Database(db_path=db_file)
    await db.init_db()

    await db.add_subscriber(chat_id=12345)

    stores = await db.get_user_stores(12345)
    assert len(stores) == len(ALL_STORES)
    assert "Epic Games" in stores

    assert await db.is_deal_allowed_for_user(12345, "Epic Games") is True
    assert await db.is_deal_allowed_for_user(12345, "Steam") is True

    new_stores = await db.toggle_user_store(12345, "Steam")
    assert "Steam" not in new_stores
    assert await db.is_deal_allowed_for_user(12345, "Steam") is False

    cleared = await db.set_user_stores(12345, set())
    assert len(cleared) == 0
    assert await db.is_deal_allowed_for_user(12345, "Epic Games") is False

@pytest.mark.asyncio
async def test_database_category_preferences(tmp_path):
    db_file = str(tmp_path / "test.db")
    db = Database(db_path=db_file)
    await db.init_db()

    await db.add_subscriber(chat_id=12345)

    cats = await db.get_user_categories(12345)
    assert len(cats) == len(ALL_CATEGORIES)
    assert "Azione" in cats

    assert await db.is_deal_category_allowed(12345, ["Action", "Indie"]) is True

    # Toggle Azione off
    await db.toggle_user_category(12345, "Azione")
    await db.toggle_user_category(12345, "Indie")

    # Only Azione & Indie deal should now be disallowed
    assert await db.is_deal_category_allowed(12345, ["Action", "Indie"]) is False
    # But RPG is still allowed
    assert await db.is_deal_category_allowed(12345, ["RPG"]) is True

@pytest.mark.asyncio
async def test_database_price_preferences(tmp_path):
    db_file = str(tmp_path / "test.db")
    db = Database(db_path=db_file)
    await db.init_db()

    await db.add_subscriber(chat_id=12345)

    min_stock, max_sale = await db.get_user_prices(chat_id=12345)
    assert min_stock == 0.0
    assert max_sale == 0.0

    # Free deal (stock: 9.99, sale: 0.0) allowed by default
    assert await db.is_deal_price_allowed(12345, stock_price_val=9.99, sale_price_val=0.0) is True

    # Paid discount (sale: 2.99) disallowed when max_sale == 0.0
    assert await db.is_deal_price_allowed(12345, stock_price_val=19.99, sale_price_val=2.99) is False

    # Set max_sale to 5.0
    await db.set_user_max_sale_price(12345, 5.0)
    assert await db.is_deal_price_allowed(12345, stock_price_val=19.99, sale_price_val=2.99) is True
    assert await db.is_deal_price_allowed(12345, stock_price_val=19.99, sale_price_val=9.99) is False

    # Set min_stock to 10.0
    await db.set_user_min_stock_price(12345, 10.0)
    # Paid deal with stock: 5.0 is disallowed
    assert await db.is_deal_price_allowed(12345, stock_price_val=5.0, sale_price_val=2.0) is False
    # Paid deal with stock: 15.0 is allowed
    assert await db.is_deal_price_allowed(12345, stock_price_val=15.0, sale_price_val=2.0) is True

    # By default, ignore_min_on_free is True, so 100% free deal with stock: 5.0 is allowed
    assert await db.get_user_ignore_min_on_free(12345) is True
    assert await db.is_deal_price_allowed(12345, stock_price_val=5.0, sale_price_val=0.0) is True

    # If user toggles ignore_min_on_free to False, 100% free deal under min_stock is blocked
    new_toggle = await db.toggle_user_ignore_min_on_free(12345)
    assert new_toggle is False
    assert await db.is_deal_price_allowed(12345, stock_price_val=5.0, sale_price_val=0.0) is False

    # Reset
    await db.reset_user_prices(12345)
    min_stock, max_sale = await db.get_user_prices(12345)
    assert min_stock == 0.0
    assert max_sale == 0.0
    assert await db.get_user_ignore_min_on_free(12345) is True

@pytest.mark.asyncio
async def test_database_quality_preferences(tmp_path):
    db_file = str(tmp_path / "test_quality.db")
    db = Database(db_path=db_file)
    await db.init_db()

    await db.add_subscriber(chat_id=12345)

    # By default, no quality filter
    min_rating, min_reviews = await db.get_user_rating_filter(12345)
    assert min_rating == 0
    assert min_reviews == 0
    assert await db.is_deal_quality_allowed(12345, rating_percent=40, reviews_count=5, store="Steam") is True
    assert await db.is_deal_quality_allowed(12345, rating_percent=None, reviews_count=None, store="Steam") is True

    # Set filter: min 70% positive, min 10 reviews
    await db.set_user_rating_filter(12345, min_rating=70, min_reviews=10)

    # Shovelware with 45% positive -> blocked
    assert await db.is_deal_quality_allowed(12345, rating_percent=45, reviews_count=100, store="Steam") is False
    # Shovelware with 90% positive but only 2 fake reviews -> blocked
    assert await db.is_deal_quality_allowed(12345, rating_percent=90, reviews_count=2, store="Steam") is False
    # Good game with 85% positive and 500 reviews -> allowed
    assert await db.is_deal_quality_allowed(12345, rating_percent=85, reviews_count=500, store="Steam") is True

    # Curated store (Epic Games) unrated -> allowed
    assert await db.is_deal_quality_allowed(12345, rating_percent=None, reviews_count=None, store="Epic Games") is True
    # Unrated on Steam with active quality filter -> blocked
    assert await db.is_deal_quality_allowed(12345, rating_percent=None, reviews_count=None, store="Steam") is False

def test_normalize_helpers():
    assert normalize_deal_store("Epic Games") == "Epic Games"
    assert normalize_deal_store("Steam") == "Steam"
    assert normalize_deal_store("GOG") == "GOG"
    assert normalize_deal_category("Action RPG") == "GDR / RPG"
    assert normalize_deal_category("Shooter FPS") == "Sparatutto"
    assert normalize_deal_category("Indie Adventure") == "Avventura"
