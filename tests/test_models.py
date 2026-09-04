"""Unit tests for GameDeal model and title cleaning."""
from free_games_bot.models import GameDeal

def test_clean_title():
    deal = GameDeal(
        id="test_1",
        title="Alone With You (Epic Games) Giveaway",
        store="Epic Games",
        stock_price="9,99 €",
        store_url="https://store.epicgames.com",
    )
    assert deal.clean_title() == "Alone With You"

def test_clean_title_complex_giveaways():
    deal1 = GameDeal(
        id="test_2",
        title="Dwarven Realms (Steam) Key Giveaway",
        store="Steam",
        stock_price="9,99 €",
        store_url="https://store.steampowered.com",
    )
    assert deal1.clean_title() == "Dwarven Realms"

    deal2 = GameDeal(
        id="test_3",
        title="NoRush! - Tower Edition (Epic Games) Giveaways",
        store="Epic Games",
        stock_price="Gratis",
        store_url="https://store.epicgames.com",
    )
    assert deal2.clean_title() == "NoRush! - Tower Edition"

def test_clean_title_no_suffix():
    deal = GameDeal(
        id="test_4",
        title="Cyberpunk 2077",
        store="Steam",
        stock_price="59,99 €",
        store_url="https://store.steampowered.com",
    )
    assert deal.clean_title() == "Cyberpunk 2077"
