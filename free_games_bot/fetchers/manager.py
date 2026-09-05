"""Deal Manager aggregating deals from multiple sources, deduplicating, and enriching metadata."""
import asyncio
import logging
import time
from typing import List, Optional, Set, Dict, Tuple
from free_games_bot.models import GameDeal
from free_games_bot.fetchers.epic import EpicGamesFetcher
from free_games_bot.fetchers.gamerpower import GamerPowerFetcher
from free_games_bot.fetchers.cheapshark import CheapSharkFetcher
from free_games_bot.fetchers.steam_enricher import SteamEnricher
from free_games_bot.fetchers.steamgriddb import SteamGridDBClient

logger = logging.getLogger(__name__)

class DealManager:
    def __init__(self, cache_ttl_seconds: int = 300):
        self.epic_fetcher = EpicGamesFetcher()
        self.gamerpower_fetcher = GamerPowerFetcher()
        self.cheapshark_fetcher = CheapSharkFetcher()
        self.steam_enricher = SteamEnricher()
        self.steamgriddb_client = SteamGridDBClient()
        self.cache_ttl = cache_ttl_seconds

        self._cached_deals: List[GameDeal] = []
        self._last_fetch_time: float = 0.0
        self._last_upper_price: float = 0.0
        self._lock = asyncio.Lock()

    async def fetch_all_deals(
        self,
        force_refresh: bool = False,
        max_sale_price: float = 0.0,
        min_stock_price: float = 0.0,
    ) -> List[GameDeal]:
        """Fetch, deduplicate, and enrich current free and discounted game deals."""
        async with self._lock:
            now = time.time()
            upper_price = max(20.0, max_sale_price)
            if not force_refresh and self._cached_deals and (now - self._last_fetch_time < self.cache_ttl) and (upper_price <= self._last_upper_price):
                return self._cached_deals

            logger.info("Fetching game deals from Epic Games, GamerPower, and CheapShark...")
            tasks = [
                self.epic_fetcher.fetch_deals(include_upcoming=True),
                self.gamerpower_fetcher.fetch_deals(),
                self.cheapshark_fetcher.fetch_deals(upper_price=upper_price, min_stock_price=0.0),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_raw_deals: List[GameDeal] = []
            for res in results:
                if isinstance(res, list):
                    all_raw_deals.extend(res)
                else:
                    logger.error(f"Error in deal fetcher: {res}")

            # Deduplicate deals
            deduped = self._deduplicate_deals(all_raw_deals)

            # Enrich metadata and covers concurrently
            enrich_tasks = [self._enrich_deal(deal) for deal in deduped]
            enriched_deals = await asyncio.gather(*enrich_tasks)

            self._cached_deals = list(enriched_deals)
            self._last_fetch_time = now
            self._last_upper_price = upper_price

            return list(enriched_deals)

    def _deduplicate_deals(self, deals: List[GameDeal]) -> List[GameDeal]:
        """Deduplicate deals across sources by normalized title and store, merging metadata."""
        seen_deals: Dict[Tuple[str, str], GameDeal] = {}
        deduped: List[GameDeal] = []

        # Priority order:
        # For free giveaways (<= 0.01): direct Epic Games first, then GamerPower (dedicated giveaway data), then Steam, then CheapShark
        # For discounted deals (> 0.01): Steam first, then CheapShark, then GamerPower
        def priority(d: GameDeal) -> int:
            if d.sale_price_value <= 0.01:
                if d.id.startswith("epic_"):
                    return 0
                if d.id.startswith("gp_"):
                    return 1
                if "steam" in d.store.lower():
                    return 2
                if d.id.startswith("cs_"):
                    return 3
                return 4
            else:
                if "steam" in d.store.lower():
                    return 0
                if d.id.startswith("cs_"):
                    return 1
                return 2

        sorted_deals = sorted(deals, key=priority)

        for deal in sorted_deals:
            if deal.store.lower() == "steam" and deal.steam_appid:
                key = (f"steam_{deal.steam_appid}", "steam")
            else:
                key = (deal.canonical_title(), deal.store.lower())

            if key in seen_deals:
                existing = seen_deals[key]
                # Merge metadata from duplicate into existing deal
                if not existing.end_date and deal.end_date:
                    existing.end_date = deal.end_date
                if not existing.description and deal.description:
                    existing.description = deal.description
                if not existing.cover_url and deal.cover_url:
                    existing.cover_url = deal.cover_url
                if existing.rating_percent is None and deal.rating_percent is not None:
                    existing.rating_percent = deal.rating_percent
                if existing.reviews_count is None and deal.reviews_count is not None:
                    existing.reviews_count = deal.reviews_count
                if existing.steam_appid is None and deal.steam_appid is not None:
                    existing.steam_appid = deal.steam_appid
                continue

            seen_deals[key] = deal
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

            # Safeguard: A deal on a non-Steam store should NEVER have a store_url pointing to Steam!
            if deal.store.lower() != "steam" and "steampowered.com" in (deal.store_url or "").lower():
                logger.warning(f"Deal '{deal.title}' on '{deal.store}' had invalid Steam URL '{deal.store_url}'. Correcting...")
                if deal.id.startswith("cs_"):
                    cs_id = deal.id.replace("cs_", "")
                    deal.store_url = f"https://www.cheapshark.com/redirect?dealID={cs_id}"
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

    async def get_new_deals(self, sent_deal_ids: Set[str], max_sale_price: float = 0.0, min_stock_price: float = 0.0) -> List[GameDeal]:
        """Return active deals that haven't been sent yet."""
        deals = await self.fetch_all_deals(max_sale_price=max_sale_price, min_stock_price=min_stock_price)
        return [d for d in deals if not d.is_upcoming and d.id not in sent_deal_ids]

    async def close(self):
        await self.epic_fetcher.close()
        await self.gamerpower_fetcher.close()
        await self.cheapshark_fetcher.close()
        await self.steam_enricher.close()
        await self.steamgriddb_client.close()
