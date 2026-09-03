"""Epic Games Store free promotions fetcher."""
import logging
from typing import List, Optional
from free_games_bot.fetchers.base import BaseFetcher
from free_games_bot.models import GameDeal

logger = logging.getLogger(__name__)

EPIC_PROMOTIONS_URL = (
    "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    "?locale=en-US&country=US&allowCountries=US"
)

class EpicGamesFetcher(BaseFetcher):
    async def fetch_deals(self, include_upcoming: bool = True) -> List[GameDeal]:
        """Fetch current and upcoming free games from Epic Games Store."""
        data = await self.fetch_json(EPIC_PROMOTIONS_URL)
        if not data:
            logger.warning("Failed to fetch Epic Games promotions data.")
            return []

        elements = (
            data.get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
        )

        deals: List[GameDeal] = []

        for item in elements:
            title = item.get("title")
            if not title:
                continue

            # Original stock price
            price_info = item.get("price", {}).get("totalPrice", {})
            fmt_price = price_info.get("fmtPrice", {})
            original_price = fmt_price.get("originalPrice") or "$0.00"
            if original_price in ("0", "$0", "$0.00", "Free"):
                original_price = "Free on Epic"

            # Image resolution
            key_images = item.get("keyImages", [])
            cover_url: Optional[str] = None
            # Priority: OfferImageWide, DieselStoreFrontWide, OfferImageTall, Thumbnail
            priority_types = ["OfferImageWide", "DieselStoreFrontWide", "OfferImageTall", "Thumbnail", "VaultClosed"]
            for p_type in priority_types:
                for img in key_images:
                    if img.get("type") == p_type and img.get("url"):
                        cover_url = img["url"]
                        break
                if cover_url:
                    break
            if not cover_url and key_images:
                cover_url = key_images[0].get("url")

            # Store URL slug resolution
            slug = item.get("productSlug") or item.get("urlSlug")
            mappings = item.get("catalogNs", {}).get("mappings", [])
            for mapping in mappings:
                if mapping.get("pageType") == "productHome" and mapping.get("pageSlug"):
                    slug = mapping["pageSlug"]
                    break

            store_url = f"https://store.epicgames.com/en-US/p/{slug}" if slug else "https://store.epicgames.com/en-US/free-games"
            description = item.get("description", "").strip()

            promotions = item.get("promotions") or {}
            promo_offers = promotions.get("promotionalOffers") or []
            upcoming_offers = promotions.get("upcomingPromotionalOffers") or []

            # 1. Active Free Games
            is_active_free = False
            end_date_str = None
            if promo_offers:
                for group in promo_offers:
                    for offer in group.get("promotionalOffers", []):
                        discount = offer.get("discountSetting", {}).get("discountPercentage")
                        if discount == 0:
                            is_active_free = True
                            end_date_str = offer.get("endDate")
                            break
                    if is_active_free:
                        break

            if is_active_free:
                deal_id = f"epic_{item.get('id', slug or title)}"
                deals.append(
                    GameDeal(
                        id=deal_id,
                        title=title,
                        store="Epic Games",
                        stock_price=original_price,
                        store_url=store_url,
                        cover_url=cover_url,
                        description=description,
                        end_date=end_date_str,
                        is_upcoming=False,
                    )
                )

            # 2. Upcoming Free Games (Teasers)
            elif include_upcoming and upcoming_offers:
                for group in upcoming_offers:
                    for offer in group.get("promotionalOffers", []):
                        discount = offer.get("discountSetting", {}).get("discountPercentage")
                        if discount == 0:
                            start_date = offer.get("startDate")
                            end_date = offer.get("endDate")
                            deal_id = f"epic_upcoming_{item.get('id', slug or title)}"
                            deals.append(
                                GameDeal(
                                    id=deal_id,
                                    title=title,
                                    store="Epic Games",
                                    stock_price=original_price if original_price != "Free on Epic" else "Free",
                                    store_url=store_url,
                                    cover_url=cover_url,
                                    description=description,
                                    end_date=f"Starts: {start_date} | Ends: {end_date}",
                                    is_upcoming=True,
                                )
                            )
                            break

        return deals
