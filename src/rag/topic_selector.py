import logging
from typing import List, Dict, Optional
from scraper.models import AgendaItem

logger = logging.getLogger(__name__)

# Keywords that signal high citizen-impact topics
HIGH_IMPACT_KEYWORDS = [
    "housing", "rent", "tenant", "eviction", "landlord", "slumlord",
    "tax", "property tax", "budget", "levy", "fee",
    "transit", "ttc", "bus", "streetcar", "subway", "fare",
    "zoning", "development", "condo", "tower", "densification",
    "shelter", "homeless", "encampment",
    "police", "safety", "crime", "gun",
    "water", "sewage", "infrastructure", "pothole", "road",
    "childcare", "daycare", "school",
    "park", "recreation", "community centre",
]


def score_agenda_item(item: AgendaItem) -> float:
    """
    Scores an agenda item by citizen-impact potential.
    Higher score = more newsworthy.
    """
    score = 0.0
    text = f"{item.title} {item.summary or ''} {item.recommendations or ''}".lower()

    # Keyword hits
    for kw in HIGH_IMPACT_KEYWORDS:
        if kw in text:
            score += 10.0

    # More PDF attachments = more substance
    score += len(item.pdf_links) * 5.0

    # Longer recommendations = more actionable
    if item.recommendations:
        score += min(len(item.recommendations) / 100, 20.0)

    # Has parsed PDF text = richer context
    if item.parsed_pdf_text:
        score += 15.0

    # Status bonuses
    if item.status and item.status.lower() in ["adopted", "approved"]:
        score += 10.0  # Already decided = newsworthy

    return score


def select_top_topic(items: List[AgendaItem], top_n: int = 1) -> List[AgendaItem]:
    """
    Picks the most impactful/newsworthy topic(s) from today's scrape.
    Returns the top_n items sorted by impact score.
    """
    if not items:
        logger.warning("No agenda items to select from.")
        return []

    scored = [(item, score_agenda_item(item)) for item in items]
    scored.sort(key=lambda x: x[1], reverse=True)

    top_items = [item for item, score in scored[:top_n]]

    for item, score in scored[:top_n]:
        logger.info(f"🎯 Selected topic: '{item.title}' (score: {score:.1f})")

    return top_items
