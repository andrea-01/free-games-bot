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

def test_extract_price_float():
    from free_games_bot.models import extract_price_float
    # Testing cases with the digit '0' that previously triggered the bug
    assert extract_price_float("10") == 10.0
    assert extract_price_float("20") == 20.0
    assert extract_price_float("5,0") == 5.0
    assert extract_price_float("15.00") == 15.0
    assert extract_price_float("100") == 100.0
    assert extract_price_float("20,50 €") == 20.50
    assert extract_price_float("10.99 €") == 10.99

    # Free and zero prices
    assert extract_price_float("0") == 0.0
    assert extract_price_float("0.00") == 0.0
    assert extract_price_float("0,00") == 0.0
    assert extract_price_float("0 €") == 0.0
    assert extract_price_float("Gratis") == 0.0
    assert extract_price_float("free") == 0.0
    assert extract_price_float("omaggio") == 0.0

    # General formats
    assert extract_price_float("19,99 €") == 19.99
    assert extract_price_float("$9.99") == 9.99
    assert extract_price_float("5") == 5.0
    assert extract_price_float(None) == 0.0
    assert extract_price_float("") == 0.0

