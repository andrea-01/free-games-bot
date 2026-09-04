"""GamerPower API fetcher for PC game giveaways across multiple stores."""
import logging
from typing import List
from free_games_bot.fetchers.base import BaseFetcher
from free_games_bot.models import GameDeal, extract_price_float, format_price_eur

logger = logging.getLogger(__name__)

GAMERPOWER_API_URL = "https://www.gamerpower.com/api/giveaways"

class GamerPowerFetcher(BaseFetcher):
    @staticmethod
    def _normalize_store(platforms: str) -> str:
        p_lower = platforms.lower()
        if "steam" in p_lower:
            return "Steam"
        if "epic" in p_lower:
            return "Epic Games"
        if "gog" in p_lower:
            return "GOG"
        if "ubisoft" in p_lower or "uplay" in p_lower:
            return "Ubisoft"
        if "origin" in p_lower or "ea" in p_lower:
            return "EA / Origin"
        if "itch" in p_lower:
            return "Itch.io"
        if "prime" in p_lower or "amazon" in p_lower:
            return "Prime Gaming"
        if "indiegala" in p_lower or "drm-free" in p_lower:
            return "IndieGala / DRM-Free"
        return platforms

    async def fetch_deals(self) -> List[GameDeal]:
        """Fetch active PC game giveaways."""
        params = {"platform": "pc", "type": "game"}
        data = await self.fetch_json(GAMERPOWER_API_URL, params=params)
        if not data or not isinstance(data, list):
            logger.warning("No data received from GamerPower API.")
            return []

        deals: List[GameDeal] = []
        for item in data:
            # Ensure it is a game
            item_type = item.get("type", "").lower()
            if item_type and item_type != "game":
                continue

            title = item.get("title", "")
            worth_raw = item.get("worth", "")
            worth_val = extract_price_float(worth_raw)
            worth = format_price_eur(worth_val) if worth_val > 0 else "Gratis"

            platforms = item.get("platforms", "PC")
            store = self._normalize_store(platforms)
            cover_url = item.get("image") or item.get("thumbnail")
            store_url = item.get("open_giveaway_url") or item.get("gamerpower_url")
            description = item.get("description", "").strip()
            end_date = item.get("end_date")
            if end_date == "N/A":
                end_date = None

            deal_id = f"gp_{item.get('id', title)}"

            deals.append(
                GameDeal(
                    id=deal_id,
                    title=title,
                    store=store,
                    stock_price=worth,
                    store_url=store_url,
                    cover_url=cover_url,
                    description=description,
                    end_date=end_date,
                    is_upcoming=False,
                )
            )

        return deals
