"""Steam metadata enricher for release year, genres, player modes, and cover art."""
import logging
import re
from typing import Dict, Any, Optional
from free_games_bot.fetchers.base import BaseFetcher
from free_games_bot.models import GameDeal

logger = logging.getLogger(__name__)

STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"

class SteamEnricher(BaseFetcher):
    def __init__(self):
        super().__init__(timeout=10.0)
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def enrich_deal(self, deal: GameDeal) -> GameDeal:
        """Enrich a deal with release year, genres, player modes, and high-res art from Steam."""
        clean_title = deal.clean_title()
        if clean_title in self._cache:
            data = self._cache[clean_title]
            return self._apply_data(deal, data)

        try:
            # 1. Search Steam for the game title
            search_params = {"term": clean_title, "l": "english", "cc": "US"}
            search_data = await self.fetch_json(STEAM_SEARCH_URL, params=search_params)
            if not search_data or not search_data.get("items"):
                return deal

            # Find matching item
            match_item = None
            for item in search_data["items"]:
                # Simple loose title matching
                item_name = item.get("name", "").lower()
                clean_lower = clean_title.lower()
                if clean_lower in item_name or item_name in clean_lower:
                    match_item = item
                    break

            if not match_item:
                match_item = search_data["items"][0]

            app_id = match_item.get("id")
            if not app_id:
                return deal

            # 2. Fetch app details
            app_params = {"appids": str(app_id), "l": "english"}
            app_data = await self.fetch_json(STEAM_APPDETAILS_URL, params=app_params)
            if not app_data or str(app_id) not in app_data or not app_data[str(app_id)].get("success"):
                return deal

            details = app_data[str(app_id)]["data"]

            # Release year
            rel_date_str = details.get("release_date", {}).get("date", "")
            year_match = re.search(r"\b(19\d\d|20\d\d)\b", rel_date_str)
            release_year = year_match.group(1) if year_match else None

            # Genres
            genres = [g.get("description", "") for g in details.get("genres", []) if g.get("description")]

            # Player modes (Single-player, Multi-player, Co-op, PvP, etc.)
            categories = [c.get("description", "") for c in details.get("categories", []) if c.get("description")]
            player_modes = []
            for cat in categories:
                cat_lower = cat.lower()
                if "single-player" in cat_lower and "Single-player" not in player_modes:
                    player_modes.append("Single-player")
                elif ("multi-player" in cat_lower or "multiplayer" in cat_lower or "online pvp" in cat_lower) and "Multi-player" not in player_modes:
                    player_modes.append("Multi-player")
                elif ("co-op" in cat_lower or "cooperative" in cat_lower) and "Co-op" not in player_modes:
                    player_modes.append("Co-op")

            header_image = details.get("header_image")
            short_desc = details.get("short_description")

            enriched_info = {
                "steam_appid": app_id,
                "release_year": release_year,
                "genres": genres,
                "player_modes": player_modes,
                "header_image": header_image,
                "short_desc": short_desc,
            }

            self._cache[clean_title] = enriched_info
            return self._apply_data(deal, enriched_info)

        except Exception as e:
            logger.debug(f"Steam enrichment skipped for {clean_title}: {e}")
            return deal

    def _apply_data(self, deal: GameDeal, data: Dict[str, Any]) -> GameDeal:
        if not deal.release_year and data.get("release_year"):
            deal.release_year = data["release_year"]

        if not deal.genres and data.get("genres"):
            deal.genres = data["genres"]

        if not deal.player_modes and data.get("player_modes"):
            deal.player_modes = data["player_modes"]

        if not deal.description and data.get("short_desc"):
            deal.description = data["short_desc"]

        if not deal.steam_appid and data.get("steam_appid"):
            deal.steam_appid = data["steam_appid"]

        # If deal has no cover or generic image, use Steam's high-res header image
        if not deal.cover_url and data.get("header_image"):
            deal.cover_url = data["header_image"]

        return deal
