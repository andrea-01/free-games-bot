"""Deal Manager aggregating deals from multiple sources and enriching metadata."""
import asyncio
import logging
import time
from typing import List, Optional, Set
from free_games_bot.models import GameDeal
from free_games_bot.fetchers.epic import EpicGamesFetcher
from free_games_bot.fetchers.gamerpower import GamerPowerFetcher
from free_games_bot.fetchers.steam_enricher import SteamEnricher
from free_games_bot.fetchers.steamgriddb import SteamGridDBClient

logger = logging.getLogger(__name__)

class DealManager:
    def __init__(self, cache_ttl_seconds: int = 300):
        self.epic_fetcher = EpicGamesFetcher()
        self.gamerpower_fetcher = GamerPowerFetcher()
        self.steam_enricher = SteamEnricher()
        self.steamgriddb_client = SteamGridDBClient()
        self.cache_ttl = cache_ttl_seconds

        self._cached_deals: List[GameDeal] = []
        self._last_fetch_time: float = 0.0
        self._lock = asyncio.Lock()

    async def fetch_all_deals(self, force_refresh: bool = False) -> List[GameDeal]:
        """Fetch, deduplicate, and enrich all current free game deals."""
        async with self._lock:
            now = time.time()
            if not force_refresh and self._cached_deals and (now - self._last_fetch_time < self.cache_ttl):
                return self._cached_deals

            logger.info("Fetching fresh game deals from Epic Games and GamerPower...")

            # Run fetchers concurrently
            epic_task = self.epic_fetcher.fetch_deals(include_upcoming=True)
            gamerpower_task = self.gamerpower_fetcher.fetch_deals()

            epic_deals, gp_deals = await asyncio.gather(
                epic_task, gamerpower_task, return_exceptions=True
            )

            all_raw_deals: List[GameDeal] = []
            if isinstance(epic_deals, list):
                all_raw_deals.extend(epic_deals)
            else:
                logger.error(f"Error fetching Epic deals: {epic_deals}")

            if isinstance(gp_deals, list):
                all_raw_deals.extend(gp_deals)
            else:
                logger.error(f"Error fetching GamerPower deals: {gp_deals}")

            # Deduplicate deals
            deduped = self._deduplicate_deals(all_raw_deals)

            # Enrich metadata and covers concurrently
            enrich_tasks = [self._enrich_deal(deal) for deal in deduped]
            enriched_deals = await asyncio.gather(*enrich_tasks)

            self._cached_deals = list(enriched_deals)
            self._last_fetch_time = now
            return self._cached_deals

    def _deduplicate_deals(self, deals: List[GameDeal]) -> List[GameDeal]:
        """Deduplicate deals across sources by normalized title and store."""
        seen_keys = set()
        deduped: List[GameDeal] = []

        # Give priority to direct Epic Games deals over GamerPower duplicates
        sorted_deals = sorted(
            deals,
            key=lambda d: 0 if d.id.startswith("epic_") else 1
        )

        for deal in sorted_deals:
            norm_title = deal.clean_title().lower()
            key = (norm_title, deal.store.lower())

            # Skip if we already have this title from this store
            if key in seen_keys:
                continue

            seen_keys.add(key)
            deduped.append(deal)

        return deduped

    async def _enrich_deal(self, deal: GameDeal) -> GameDeal:
        """Enrich deal with Steam metadata and SteamGridDB cover if available."""
        try:
            # 1. Enrich from Steam (release year, tags, player modes)
            deal = await self.steam_enricher.enrich_deal(deal)

            # 2. If SteamGridDB is available, attempt to get high-res vertical box art
            if self.steamgriddb_client.is_available:
                sgdb_cover = await self.steamgriddb_client.get_cover_url(deal)
                if sgdb_cover:
                    deal.cover_url = sgdb_cover
        except Exception as e:
            logger.debug(f"Enrichment error for {deal.title}: {e}")

        return deal

    async def get_active_deals(self, store_filter: Optional[str] = None) -> List[GameDeal]:
        """Return currently active free game deals, optionally filtered by store."""
        deals = await self.fetch_all_deals()
        active = [d for d in deals if not d.is_upcoming]
        if store_filter:
            store_filter_lower = store_filter.lower()
            return [d for d in active if store_filter_lower in d.store.lower()]
        return active

    async def get_epic_deals(self) -> List[GameDeal]:
        """Return Epic Games deals including active and upcoming."""
        deals = await self.fetch_all_deals()
        return [d for d in deals if d.store.lower() == "epic games"]

    async def get_steam_deals(self) -> List[GameDeal]:
        """Return Steam free deals."""
        deals = await self.fetch_all_deals()
        return [d for d in deals if "steam" in d.store.lower()]

    async def get_new_deals(self, sent_deal_ids: Set[str]) -> List[GameDeal]:
        """Return active deals that haven't been sent yet."""
        deals = await self.fetch_all_deals()
        # Only broadcast active giveaways (not upcoming teasers)
        return [d for d in deals if not d.is_upcoming and d.id not in sent_deal_ids]

    async def close(self):
        await self.epic_fetcher.close()
        await self.gamerpower_fetcher.close()
        await self.steam_enricher.close()
        await self.steamgriddb_client.close()
