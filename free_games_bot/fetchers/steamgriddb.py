"""SteamGridDB API client for fetching high-resolution box art covers."""
import logging
import urllib.parse
from typing import Optional, Dict
from free_games_bot.config import config
from free_games_bot.fetchers.base import BaseFetcher
from free_games_bot.models import GameDeal

logger = logging.getLogger(__name__)

BASE_SGDB_URL = "https://www.steamgriddb.com/api/v2"

class SteamGridDBClient(BaseFetcher):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(timeout=10.0)
        self.api_key = (api_key or config.steamgriddb_api_key).strip()
        self._cache: Dict[str, Optional[str]] = {}

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    async def get_cover_url(self, deal: GameDeal) -> Optional[str]:
        """Fetch vertical poster grid (600x900) from SteamGridDB."""
        if not self.is_available:
            return None

        clean_title = deal.clean_title()
        if clean_title in self._cache:
            return self._cache[clean_title]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            # 1. If Steam AppID is available, try direct Steam ID lookup
            if deal.steam_appid:
                grid_url = f"{BASE_SGDB_URL}/grids/steam/{deal.steam_appid}?dimensions=600x900"
                grid_data = await self.fetch_json(grid_url, headers=headers)
                if grid_data and grid_data.get("success") and grid_data.get("data"):
                    cover = grid_data["data"][0].get("url")
                    if cover:
                        self._cache[clean_title] = cover
                        return cover

            # 2. Search game by autocomplete
            encoded_title = urllib.parse.quote(clean_title)
            search_url = f"{BASE_SGDB_URL}/search/autocomplete/{encoded_title}"
            search_data = await self.fetch_json(search_url, headers=headers)
            if not search_data or not search_data.get("success") or not search_data.get("data"):
                self._cache[clean_title] = None
                return None

            game_id = search_data["data"][0].get("id")
            if not game_id:
                self._cache[clean_title] = None
                return None

            # 3. Retrieve 600x900 grid
            grid_url = f"{BASE_SGDB_URL}/grids/game/{game_id}?dimensions=600x900"
            grid_data = await self.fetch_json(grid_url, headers=headers)
            if grid_data and grid_data.get("success") and grid_data.get("data"):
                cover = grid_data["data"][0].get("url")
                self._cache[clean_title] = cover
                return cover

        except Exception as e:
            logger.debug(f"SteamGridDB lookup failed for '{clean_title}': {e}")

        self._cache[clean_title] = None
        return None
