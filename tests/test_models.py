"""Unit tests for GameDeal model."""
from free_games_bot.models import GameDeal

def test_clean_title():
    deal = GameDeal(
        id="test_1",
        title="Alone With You (Epic Games) Giveaway",
        store="Epic Games",
        stock_price="$9.99",
        store_url="https://store.epicgames.com",
    )
    assert deal.clean_title() == "Alone With You"

def test_clean_title_no_suffix():
    deal = GameDeal(
        id="test_2",
        title="Cyberpunk 2077",
        store="Steam",
        stock_price="$59.99",
        store_url="https://store.steampowered.com",
    )
    assert deal.clean_title() == "Cyberpunk 2077"
