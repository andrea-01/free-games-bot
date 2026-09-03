"""Data models for free game deals."""
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class GameDeal:
    id: str  # Unique deal identifier (e.g. epic_alone-with-you-028a15 or gp_1234)
    title: str
    store: str  # e.g. "Epic Games", "Steam", "GOG", "Ubisoft", "EA / Origin", "Itch.io"
    stock_price: str  # e.g. "$9.99" or "€19.99"
    store_url: str  # Direct link to store page
    cover_url: Optional[str] = None  # High-res cover art URL
    description: Optional[str] = None  # Short synopsis/description
    release_year: Optional[str] = None  # e.g. "2016"
    genres: List[str] = field(default_factory=list)  # e.g. ["Action", "Sci-Fi"]
    player_modes: List[str] = field(default_factory=list)  # e.g. ["Single-player", "Multi-player"]
    end_date: Optional[str] = None  # e.g. "2026-09-10 15:00 UTC"
    is_upcoming: bool = False  # True if deal starts in future (upcoming Epic free game)
    steam_appid: Optional[int] = None

    def clean_title(self) -> str:
        """Strip trailing giveaway suffixes from titles."""
        clean = self.title
        for suffix in ["Giveaway", "Key Giveaway", "(Epic Games)", "(Steam)", "(GOG)", "(Itch.io)"]:
            clean = clean.replace(suffix, "").strip()
        return clean.strip(" -:")
