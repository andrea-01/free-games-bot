"""Steam metadata enricher and fallback extractor for release year, genres, player modes, and description."""
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from free_games_bot.fetchers.base import BaseFetcher
from free_games_bot.models import GameDeal

logger = logging.getLogger(__name__)

STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"

def extract_fallback_metadata(description: Optional[str]) -> Tuple[List[str], List[str], Optional[str]]:
    """Extract genres, player modes, and possible release year from deal description or text."""
    d = (description or "").lower()
    genres = []

    if any(w in d for w in ["action", "azione", "brawler", "picchiaduro", "combattimento"]):
        genres.append("Azione")
    if any(w in d for w in ["adventure", "avventura", "esplora", "point-and-click", "storia", "narrativa"]):
        genres.append("Avventura")
    if any(w in d for w in ["rpg", "gdr", "ruolo", "roguelike", "roguelite", "dungeon"]):
        genres.append("GDR / RPG")
    if any(w in d for w in ["strategy", "strategia", "rts", "deckbuilder", "carte", "tattico", "tactical"]):
        genres.append("Strategia")
    if any(w in d for w in ["shooter", "sparatutto", "fps"]):
        genres.append("Sparatutto")
    if any(w in d for w in ["puzzle", "rompicapo", "enigmi", "wordle"]):
        genres.append("Puzzle")
    if any(w in d for w in ["simulation", "simulazione", "simulator"]):
        genres.append("Simulazione")
    if any(w in d for w in ["horror", "psicologico", "terror", "spaventoso"]):
        genres.append("Horror")
    if any(w in d for w in ["indie", "visual novel", "casual", "passatempo", "2d"]):
        if "Indie" not in genres:
            genres.append("Indie")

    if not genres:
        genres.append("Indie")

    modes = []
    if any(w in d for w in ["multiplayer", "multigiocatore", "online", "pvp", "arena", "brawler"]):
        modes.append("Multigiocatore")
    if any(w in d for w in ["co-op", "cooperativa"]):
        modes.append("Co-op")
    if not modes:
        modes.append("Giocatore singolo")

    # Search for year (1990-2029)
    year_match = re.search(r"\b(199\d|20[0-2]\d)\b", description or "")
    year = year_match.group(1) if year_match else None

    return genres, modes, year

class SteamEnricher(BaseFetcher):
    def __init__(self):
        super().__init__(timeout=10.0)
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def enrich_deal(self, deal: GameDeal) -> GameDeal:
        """Enrich deal with release year, genres, player modes, and Italian synopsis."""
        clean_title = deal.clean_title()
        cache_key = str(deal.steam_appid) if deal.steam_appid else clean_title

        if cache_key in self._cache:
            data = self._cache[cache_key]
            return self._apply_data(deal, data)

        app_id = deal.steam_appid

        # If app_id not pre-known, perform multi-step Steam search
        if not app_id:
            search_candidates = [clean_title]
            if " - " in clean_title:
                search_candidates.append(clean_title.split(" - ")[0].strip())
            if ":" in clean_title:
                search_candidates.append(clean_title.split(":")[0].strip())
            if "." in clean_title:
                search_candidates.append(clean_title.replace(".", " ").strip())

            for candidate in search_candidates:
                if len(candidate) < 2:
                    continue
                try:
                    search_params = {"term": candidate, "l": "italian", "cc": "IT"}
                    search_data = await self.fetch_json(STEAM_SEARCH_URL, params=search_params)
                    if search_data and search_data.get("items"):
                        match_item = None
                        for item in search_data["items"]:
                            item_name = item.get("name", "").lower()
                            clean_lower = candidate.lower()
                            if clean_lower in item_name or item_name in clean_lower:
                                match_item = item
                                break
                        if not match_item:
                            match_item = search_data["items"][0]

                        app_id = match_item.get("id")
                        if app_id:
                            break
                except Exception as e:
                    logger.debug(f"Search failed for '{candidate}': {e}")

        # If Steam app_id resolved, fetch full app details in Italian
        if app_id:
            try:
                app_params = {"appids": str(app_id), "l": "italian", "cc": "IT"}
                app_data = await self.fetch_json(STEAM_APPDETAILS_URL, params=app_params)
                if app_data and str(app_id) in app_data and app_data[str(app_id)].get("success"):
                    details = app_data[str(app_id)]["data"]

                    rel_date_str = details.get("release_date", {}).get("date", "")
                    year_match = re.search(r"\b(19\d\d|20\d\d)\b", rel_date_str)
                    release_year = year_match.group(1) if year_match else None

                    genres = [g.get("description", "") for g in details.get("genres", []) if g.get("description")]

                    categories = [c.get("description", "") for c in details.get("categories", []) if c.get("description")]
                    player_modes = []
                    for cat in categories:
                        cat_lower = cat.lower()
                        if any(x in cat_lower for x in ["single-player", "singolo", "giocatore singolo"]) and "Giocatore singolo" not in player_modes:
                            player_modes.append("Giocatore singolo")
                        elif any(x in cat_lower for x in ["multi-player", "multiplayer", "multigiocatore", "pvp"]) and "Multigiocatore" not in player_modes:
                            player_modes.append("Multigiocatore")
                        elif any(x in cat_lower for x in ["co-op", "cooperativa"]) and "Co-op" not in player_modes:
                            player_modes.append("Co-op")

                    if not player_modes:
                        player_modes = ["Giocatore singolo"]

                    header_image = details.get("header_image")
                    short_desc = details.get("short_description")

                    price_overview = details.get("price_overview") or {}
                    eur_price = price_overview.get("initial_formatted") or price_overview.get("final_formatted")

                    enriched_info = {
                        "steam_appid": app_id,
                        "release_year": release_year,
                        "genres": genres,
                        "player_modes": player_modes,
                        "header_image": header_image,
                        "short_desc": short_desc,
                        "eur_price": eur_price,
                    }

                    self._cache[cache_key] = enriched_info
                    return self._apply_data(deal, enriched_info)
            except Exception as e:
                logger.debug(f"Steam appdetails failed for {app_id}: {e}")

        # Fallback enrichment when Steam search yields no match (e.g. Itch.io exclusives)
        fb_genres, fb_modes, fb_year = extract_fallback_metadata(deal.description)
        fallback_info = {
            "steam_appid": deal.steam_appid,
            "release_year": fb_year,
            "genres": fb_genres,
            "player_modes": fb_modes,
            "header_image": None,
            "short_desc": None,
            "eur_price": None,
        }
        self._cache[cache_key] = fallback_info
        return self._apply_data(deal, fallback_info)

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
            if deal.store.lower() == "steam":
                deal.store_url = f"https://store.steampowered.com/app/{deal.steam_appid}/?l=italian"

        if ("$" in deal.stock_price or not deal.stock_price) and data.get("eur_price"):
            deal.stock_price = data["eur_price"]

        if not deal.cover_url and data.get("header_image"):
            deal.cover_url = data["header_image"]

        # Final safety defaults so fields are NEVER empty
        if not deal.genres:
            deal.genres = ["Indie"]
        if not deal.player_modes:
            deal.player_modes = ["Giocatore singolo"]
        if not deal.description:
            deal.description = f"Approfitta dell'offerta per {deal.clean_title()} disponibile su {deal.store}."

        return deal
