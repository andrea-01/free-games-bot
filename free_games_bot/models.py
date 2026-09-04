"""Data models for free and discounted game deals."""
import re
from dataclasses import dataclass, field
from typing import List, Optional

def extract_price_float(price_str: Optional[str]) -> float:
    """Extract float numeric value from price strings like '19,99 €', '$9.99', 'Gratis', etc."""
    if not price_str:
        return 0.0
    s = price_str.lower().strip()
    if any(word in s for word in ["gratis", "free", "omaggio", "0", "0.00", "0,00"]):
        return 0.0
    # Match first floating point number
    match = re.search(r"(\d+([.,]\d+)?)", s)
    if match:
        num_str = match.group(1).replace(",", ".")
        try:
            return float(num_str)
        except ValueError:
            return 0.0
    return 0.0

def format_price_eur(amount: float) -> str:
    """Format float amount into Italian Euro string e.g. '19,99 €'."""
    if amount <= 0.001:
        return "Gratis"
    return f"{amount:.2f}".replace(".", ",") + " €"

@dataclass
class GameDeal:
    id: str  # Unique deal identifier (e.g. epic_alone-with-you-028a15, gp_1234, cs_dealId)
    title: str
    store: str  # e.g. "Epic Games", "Steam", "GOG", "Ubisoft", "EA / Origin", "Itch.io"
    stock_price: str  # Original list price string (e.g. "19,99 €")
    store_url: str  # Direct link to store page in Italian where possible
    cover_url: Optional[str] = None  # High-res cover art URL
    description: Optional[str] = None  # Synopsis in Italian if available
    release_year: Optional[str] = None  # e.g. "2016"
    genres: List[str] = field(default_factory=list)  # e.g. ["Azione", "Fantascienza"]
    player_modes: List[str] = field(default_factory=list)  # e.g. ["Giocatore singolo", "Multigiocatore"]
    end_date: Optional[str] = None  # Expiration date
    is_upcoming: bool = False  # True for future Epic games
    steam_appid: Optional[int] = None
    sale_price_value: float = 0.0  # 0.0 if 100% free
    rating_percent: Optional[int] = None  # e.g. 85 (% positive reviews)
    reviews_count: Optional[int] = None  # e.g. 1500 (total reviews)
    metacritic_score: Optional[int] = None  # e.g. 82

    @property
    def stock_price_value(self) -> float:
        return extract_price_float(self.stock_price)

    def clean_title(self) -> str:
        """Strip trailing store tags and giveaway/key suffixes from titles."""
        clean = re.sub(
            r"\((Steam|Epic Games|GOG|Itch\.io|itchio|IndieGala|Stove|PC|DRM-Free|Ubisoft|EA|itch\.io)\)",
            "",
            self.title,
            flags=re.IGNORECASE,
        )
        clean = re.sub(
            r"\b(Steam\s+Key|Beta\s+Key|Key\s+Giveaways?|Key|Giveaways?|Free|Gratis|Offerta)\b",
            "",
            clean,
            flags=re.IGNORECASE,
        )
        return re.sub(r"\s+", " ", clean).strip(" -:–")
