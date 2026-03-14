import logging
from typing import List, Dict, Optional
from scraper.models import AgendaItem

logger = logging.getLogger(__name__)

# Keywords that signal high citizen-impact topics
HIGH_IMPACT_KEYWORDS = [
    "housing", "rent", "tenant", "eviction", "landlord", "slumlord", "affordable", "homeless", "encampment", "shelter",
    "tax", "property tax", "budget", "levy", "fee", "funding", "financial",
    "transit", "ttc", "bus", "streetcar", "subway", "fare", "bike", "cycling", "lane", "road", "pothole", "construction",
    "zoning", "development", "condo", "tower", "densification", "heritage", "planning",
    "police", "safety", "crime", "gun", "enforcement", "tps",
    "water", "sewage", "infrastructure", "utility", "waste", "garbage", "environment", "climate", "net zero",
    "childcare", "daycare", "school", "youth", "senior", "library",
    "park", "recreation", "community centre", "equity", "accessibility", "inclusion",
    "economy", "business", "employment", "job", "bylaw", "regulation"
]


# Topics that usually put people to sleep (administrative/minor)
BORING_KEYWORDS = [
    "variance", "minor variance", "signage", "encroachment", "front yard", "fence",
    "item for information", "administrative", "correction", "routine", "technical"
]

# Topics that people get fired up about (boost these)
HOT_KEYWORDS = [
    "rent", "eviction", "property tax", "police", "ttc", "fare increase", 
    "housing", "shelter", "homeless", "budget", "safety"
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
            
    # Hot topic boost
    for kw in HOT_KEYWORDS:
        if kw in text:
            score += 20.0

    # Boring penalty (unless it's a hot topic too)
    for kw in BORING_KEYWORDS:
        if kw in text:
            score -= 40.0

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

    for item, score in scored:
        logger.info(f"📊 Scored Item: '{item.title[:60]}...' | Score: {score:.1f}")

    top_items = [item for item, score in scored[:top_n]]

    for item, score in scored[:top_n]:
        logger.info(f"🎯 Selected topic: '{item.title}' (score: {score:.1f})")

    return top_items
