"""CheapShark deals fetcher for discounted PC games."""
import logging
from typing import List, Dict, Optional
from free_games_bot.fetchers.base import BaseFetcher
from free_games_bot.models import GameDeal, extract_price_float, format_price_eur

logger = logging.getLogger(__name__)

CHEAPSHARK_DEALS_URL = "https://www.cheapshark.com/api/1.0/deals"
CHEAPSHARK_STORES_URL = "https://www.cheapshark.com/api/1.0/stores"

STORE_MAP = {
    "1": "Steam",
    "2": "GamersGate",
    "3": "GreenManGaming",
    "7": "GOG",
    "8": "EA / Origin",
    "11": "Humble Store",
    "25": "Epic Games",
    "31": "Blizzard Battle.net",
}

class CheapSharkFetcher(BaseFetcher):
    def __init__(self):
        super().__init__(timeout=12.0)
        self._custom_headers = {
            "User-Agent": "FreeGamesTelegramBot/1.0 (https://github.com/andrea-01/free-games-bot)"
        }

    async def fetch_deals(self, upper_price: float = 5.0, min_stock_price: float = 0.0) -> List[GameDeal]:
        """Fetch discounted game deals from CheapShark with sale price <= upper_price."""
        if upper_price <= 0:
            return []

        params = {
            "upperPrice": str(round(upper_price, 2)),
            "sortBy": "Savings",
            "pageSize": "40",
        }

        data = await self.fetch_json(CHEAPSHARK_DEALS_URL, headers=self._custom_headers, params=params)
        if not data or not isinstance(data, list):
            logger.warning("No response from CheapShark API.")
            return []

        deals: List[GameDeal] = []
        for item in data:
            title = item.get("title", "")
            deal_id = item.get("dealID", "")
            sale_price = float(item.get("salePrice", 0.0))
            normal_price = float(item.get("normalPrice", 0.0))

            if min_stock_price > 0 and normal_price < min_stock_price:
                continue

            store_id = str(item.get("storeID", "1"))
            store_name = STORE_MAP.get(store_id, "PC Deal")

            steam_app_id = item.get("steamAppID")
            if steam_app_id and steam_app_id != "0":
                store_url = f"https://store.steampowered.com/app/{steam_app_id}/?l=italian"
                appid_int = int(steam_app_id)
            else:
                store_url = f"https://www.cheapshark.com/redirect?dealID={deal_id}"
                appid_int = None

            stock_price_str = format_price_eur(normal_price)

            deals.append(
                GameDeal(
                    id=f"cs_{deal_id[:16]}",
                    title=title,
                    store=store_name,
                    stock_price=stock_price_str,
                    store_url=store_url,
                    cover_url=item.get("thumb"),
                    sale_price_value=sale_price,
                    steam_appid=appid_int,
                )
            )

        return deals
