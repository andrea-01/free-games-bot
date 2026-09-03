"""Unit tests for deal fetchers and deduplication logic."""
import pytest
from unittest.mock import AsyncMock, patch
from free_games_bot.fetchers.epic import EpicGamesFetcher
from free_games_bot.fetchers.gamerpower import GamerPowerFetcher
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
                            "description": "An awesome game.",
                            "price": {
                                "totalPrice": {
                                    "fmtPrice": {
                                        "originalPrice": "$19.99"
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
        assert deal.stock_price == "$19.99"
        assert deal.cover_url == "https://img.epic.com/wide.jpg"
        assert deal.store_url == "https://store.epicgames.com/en-US/p/super-game"
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
            "type": "DLC",  # Should be filtered out
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
        assert deal.stock_price == "$4.99"
        assert deal.cover_url == "https://img.gamerpower.com/indie.jpg"

@pytest.mark.asyncio
async def test_deal_manager_deduplication():
    manager = DealManager()

    deal_epic = GameDeal(
        id="epic_alone_with_you",
        title="Alone With You",
        store="Epic Games",
        stock_price="$9.99",
        store_url="https://store.epicgames.com/p/alone-with-you",
    )
    deal_gp_duplicate = GameDeal(
        id="gp_999",
        title="Alone With You (Epic Games) Giveaway",
        store="Epic Games",
        stock_price="$9.99",
        store_url="https://gamerpower.com/open/alone-with-you",
    )
    deal_steam = GameDeal(
        id="steam_portal",
        title="Portal",
        store="Steam",
        stock_price="$9.99",
        store_url="https://store.steampowered.com/app/400",
    )

    deduped = manager._deduplicate_deals([deal_gp_duplicate, deal_epic, deal_steam])
    assert len(deduped) == 2
    # Should keep epic_alone_with_you and steam_portal
    stores_and_titles = [(d.clean_title(), d.store) for d in deduped]
    assert ("Alone With You", "Epic Games") in stores_and_titles
    assert ("Portal", "Steam") in stores_and_titles
