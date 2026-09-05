"""Unit tests for deal fetchers, CheapShark, and deduplication logic."""
import pytest
from unittest.mock import AsyncMock, patch
from free_games_bot.fetchers.epic import EpicGamesFetcher
from free_games_bot.fetchers.gamerpower import GamerPowerFetcher
from free_games_bot.fetchers.cheapshark import CheapSharkFetcher
from free_games_bot.fetchers.manager import DealManager
from free_games_bot.models import GameDeal

@pytest.mark.asyncio
async def test_epic_fetcher_parsing():
    fetcher = EpicGamesFetcher()
    mock_payload = {
        "data": {
            "Catalog": {
                "searchStore": {
                    "elements": [
                        {
                            "id": "epic_game_1",
                            "title": "Super Game",
                            "description": "Un gioco fantastico.",
                            "price": {
                                "totalPrice": {
                                    "fmtPrice": {
                                        "originalPrice": "19,99 €"
                                    }
                                }
                            },
                            "keyImages": [
                                {"type": "OfferImageWide", "url": "https://img.epic.com/wide.jpg"}
                            ],
                            "productSlug": "super-game",
                            "promotions": {
                                "promotionalOffers": [
                                    {
                                        "promotionalOffers": [
                                            {
                                                "discountSetting": {"discountPercentage": 0},
                                                "endDate": "2026-09-10T15:00:00.000Z"
                                            }
                                        ]
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    }

    with patch.object(fetcher, "fetch_json", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_payload
        deals = await fetcher.fetch_deals()

        assert len(deals) == 1
        deal = deals[0]
        assert deal.title == "Super Game"
        assert deal.store == "Epic Games"
        assert deal.stock_price == "19,99 €"
        assert deal.cover_url == "https://img.epic.com/wide.jpg"
        assert deal.store_url == "https://store.epicgames.com/it/p/super-game"
        assert deal.is_upcoming is False

@pytest.mark.asyncio
async def test_gamerpower_fetcher_parsing():
    fetcher = GamerPowerFetcher()
    mock_payload = [
        {
            "id": 101,
            "title": "Indie Quest (Steam) Giveaway",
            "worth": "$4.99",
            "platforms": "PC, Steam",
            "type": "Game",
            "image": "https://img.gamerpower.com/indie.jpg",
            "open_giveaway_url": "https://gamerpower.com/open/101",
            "description": "Fun indie quest.",
            "end_date": "2026-09-15 23:59:00"
        },
        {
            "id": 102,
            "title": "In-Game Gold Pack",
            "worth": "$1.99",
            "platforms": "PC",
            "type": "DLC",
            "open_giveaway_url": "https://gamerpower.com/open/102"
        }
    ]

    with patch.object(fetcher, "fetch_json", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_payload
        deals = await fetcher.fetch_deals()

        assert len(deals) == 1
        deal = deals[0]
        assert deal.title == "Indie Quest (Steam) Giveaway"
        assert deal.store == "Steam"
        assert deal.stock_price == "4,99 €"
        assert deal.cover_url == "https://img.gamerpower.com/indie.jpg"

@pytest.mark.asyncio
async def test_cheapshark_fetcher_parsing():
    fetcher = CheapSharkFetcher()
    mock_payload = [
        {
            "dealID": "deal1234567890",
            "title": "Bioshock Infinite",
            "salePrice": "4.99",
            "normalPrice": "29.99",
            "storeID": "1",
            "steamAppID": "8870",
            "thumb": "https://img.cheapshark.com/bio.jpg",
        }
    ]

    with patch.object(fetcher, "fetch_json", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_payload
        deals = await fetcher.fetch_deals(upper_price=5.0, min_stock_price=10.0)

        assert len(deals) == 1
        deal = deals[0]
        assert deal.title == "Bioshock Infinite"
        assert deal.store == "Steam"
        assert deal.sale_price_value == 4.99
        assert deal.stock_price == "29,99 €"
        assert deal.store_url == "https://store.steampowered.com/app/8870/?l=italian"

@pytest.mark.asyncio
async def test_cheapshark_fetcher_non_steam_url():
    fetcher = CheapSharkFetcher()
    mock_payload = [
        {
            "dealID": "dealEpic999",
            "title": "Beach Invasion 1944",
            "salePrice": "0.00",
            "normalPrice": "9.99",
            "storeID": "25",  # Epic Games
            "steamAppID": "2209680",
            "thumb": "https://img.cheapshark.com/beach.jpg",
        }
    ]

    with patch.object(fetcher, "fetch_json", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_payload
        deals = await fetcher.fetch_deals(upper_price=5.0)

        assert len(deals) == 1
        deal = deals[0]
        assert deal.title == "Beach Invasion 1944"
        assert deal.store == "Epic Games"
        # Must NOT point to Steam store!
        assert "steampowered.com" not in deal.store_url
        assert deal.store_url == "https://www.cheapshark.com/redirect?dealID=dealEpic999"
        # But steam_appid must still be saved for metadata enrichment
        assert deal.steam_appid == 2209680

@pytest.mark.asyncio
async def test_deal_manager_deduplication():
    manager = DealManager()

    deal_epic = GameDeal(
        id="epic_alone_with_you",
        title="Alone With You",
        store="Epic Games",
        stock_price="9,99 €",
        store_url="https://store.epicgames.com/it/p/alone-with-you",
    )
    deal_gp_duplicate = GameDeal(
        id="gp_999",
        title="Alone With You (Epic Games) Giveaway",
        store="Epic Games",
        stock_price="9,99 €",
        store_url="https://gamerpower.com/open/alone-with-you",
        end_date="2026-09-10",
    )
    deal_cs_beach = GameDeal(
        id="cs_beach",
        title="Beach Invasion 1944",
        store="Epic Games",
        stock_price="9,99 €",
        sale_price_value=0.0,
        store_url="https://www.cheapshark.com/redirect?dealID=beach",
        rating_percent=84,
        reviews_count=1000,
    )
    deal_gp_beach = GameDeal(
        id="gp_beach",
        title="Beach Invasion 1944 (Epic Games) Giveaway",
        store="Epic Games",
        stock_price="9,99 €",
        sale_price_value=0.0,
        store_url="https://gamerpower.com/open/beach-invasion-1944",
        end_date="2026-09-07",
    )
    deal_steam = GameDeal(
        id="steam_portal",
        title="Portal",
        store="Steam",
        stock_price="9,99 €",
        store_url="https://store.steampowered.com/app/400/?l=italian",
    )

    deal_gp_norush = GameDeal(
        id="gp_norush",
        title="NoRush! - Tower Edition (Epic Games) Giveaways",
        store="Epic Games",
        stock_price="2,99 €",
        sale_price_value=0.0,
        store_url="https://gamerpower.com/open/norush",
        end_date="2026-09-09",
    )
    deal_cs_norush = GameDeal(
        id="cs_norush",
        title="NoRush!",
        store="Epic Games",
        stock_price="2,49 €",
        sale_price_value=0.0,
        store_url="https://cheapshark.com/redirect?norush",
    )

    deduped = manager._deduplicate_deals([deal_gp_duplicate, deal_epic, deal_cs_beach, deal_gp_beach, deal_steam, deal_gp_norush, deal_cs_norush])
    assert len(deduped) == 4
    stores_and_titles = [(d.clean_title(), d.store) for d in deduped]
    assert ("Alone With You", "Epic Games") in stores_and_titles
    assert ("Beach Invasion 1944", "Epic Games") in stores_and_titles
    assert ("Portal", "Steam") in stores_and_titles
    assert any("NoRush" in title for title, store in stores_and_titles if store == "Epic Games")

    # Verify Beach Invasion merged GamerPower URL/end_date and CheapShark rating
    beach = next(d for d in deduped if d.clean_title() == "Beach Invasion 1944")
    assert beach.store_url == "https://gamerpower.com/open/beach-invasion-1944"
    assert beach.end_date == "2026-09-07"
    assert beach.rating_percent == 84
    assert beach.reviews_count == 1000

    # Verify NoRush deduplicated to 1 item
    norush_matches = [d for d in deduped if "NoRush" in d.clean_title()]
    assert len(norush_matches) == 1
    assert norush_matches[0].end_date == "2026-09-09"
