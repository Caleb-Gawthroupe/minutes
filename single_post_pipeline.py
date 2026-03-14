import logging
import asyncio
import os
import sys
import time
import json
import random
import string
import re

# Add src to sys.path so modules can be found
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from scraper.open_data import OpenDataClient
from scraper.tmmis import TMMISScraper
from scraper.bylaws_registry import BylawRegistryScraper
from ai.agent import CivicAIAgent
from rag.vector_store import CivicVectorStore
from rag.chunker import chunk_document
from rag.topic_selector import select_top_topic
from instagram_poster import post_carousel_to_instagram
from visuals.renderer import SocialCardRenderer
from visuals.uploader import ImgBBUploader
from visuals.source import ImageSource
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def run_single_post_pipeline():
    load_dotenv()
    logger.info("🚀 Starting Automated Meeting-Centric Pipeline...")

    # ── 1. SCRAPE LATEST MEETING ──
    # Using an empty string or broad search to get the absolute latest items
    tmmis = TMMISScraper(download_dir="downloads/tmmis")
    items = await tmmis.fetch_agenda_items_async("") # Scrape everything latest
    logger.info(f"📋 Scraped {len(items)} items from the latest council meeting.")

    if not items:
        logger.error("❌ No items found. Exiting.")
        return

    # ── 2. SELECT TOP TOPIC ──
    top_items = select_top_topic(items, top_n=1)
    topic = top_items[0]
    topic_data = topic.model_dump()
    logger.info(f"🎯 Top topic: '{topic.title}' ({topic.item_number})")

    # ── 3. DYNAMIC BYLAW DETECTION ──
    import re
    # Look for patterns like "Bylaw 123-2024" or "Bylaw No. 456-2025"
    bylaw_regex = r"(?:Bylaw|By-law)(?:\s+No\.)?\s+(\d+)-(20\d{2})"
    text_to_scan = f"{topic.title} {topic.summary or ''} {topic.recommendations or ''}"
    match = re.search(bylaw_regex, text_to_scan, re.IGNORECASE)
    
    related_bylaw_doc = None
    if match:
        b_num, b_year = match.groups()
        logger.info(f"🔗 Detected related Bylaw: {b_num}-{b_year}. Fetching details...")
        bylaw_scraper = BylawRegistryScraper(download_dir="downloads/bylaws")
        related_bylaw_doc = await bylaw_scraper.check_bylaw_status_async(int(b_year), b_num)

    # ── 4. INGEST INTO VECTOR STORE ──
    vector_store = CivicVectorStore()
    total_ingested = 0

    # Ingest ALL items from today to build context
    for item in items:
        text_parts = []
        if item.summary: text_parts.append(item.summary)
        if item.recommendations: text_parts.append(item.recommendations)
        if item.parsed_pdf_text: text_parts.append(item.parsed_pdf_text)

        combined_text = "\n".join(text_parts)
        if combined_text.strip():
            chunks = chunk_document(combined_text, metadata={
                "source": item.item_number,
                "title": item.title,
                "doc_type": "agenda_item",
                "status": item.status or "unknown",
                "is_current": "true"
            })
            total_ingested += vector_store.ingest(chunks)

    # Ingest the specific bylaw if found
    if related_bylaw_doc and related_bylaw_doc.raw_text:
        chunks = chunk_document(related_bylaw_doc.raw_text, metadata={
            "source": str(related_bylaw_doc.source_url),
            "title": related_bylaw_doc.metadata.title or f"Bylaw {b_num}-{b_year}",
            "doc_type": "bylaw",
            "is_current": "true"
        })
        total_ingested += vector_store.ingest(chunks)

    stats = vector_store.get_stats()
    logger.info(f"🗄️  Vector store: {stats['total_chunks']} total chunks ({total_ingested} new)")

    # ── 5. RETRIEVE CONTEXT (Prioritize Current + Search History) ──
    search_query = f"{topic.title} {topic.summary or ''}"
    # Retrieval logic could be enhanced here to prefer is_current="true"
    historical_context = vector_store.search(search_query, k=8)
    logger.info(f"🔍 Retrieved {len(historical_context)} context chunks.")

    # ── 6. AI CAROUSEL GENERATION ──
    ai_agent = CivicAIAgent()
    ai_payload = await ai_agent.generate_deep_dive_post_async(topic_data, historical_context)

    caption = ai_payload.get('caption', 'New from Toronto council! Swipe for details. 🏙️')
    
    # 🔗 Append the source meeting link for transparency
    if topic.source_meeting_url:
        caption += f"\n\n🔗 Read the full meeting details here: {topic.source_meeting_url}"
    
    # 🆔 Generate and append Unique Identifier (UID)
    # Use first 4 letters of title + 2 random digits
    clean_title = re.sub(r'[^A-Za-z]', '', topic.title).upper()
    prefix = clean_title[:4] if len(clean_title) >= 4 else "MMIS"
    suffix = ''.join(random.choices(string.digits, k=2))
    uid = f"{prefix}{suffix}"
    
    caption += f"\n\n💬 DM us \"{uid}\" to get the full report instantly!"
    
    logger.info(f"✨ Generated UID: {uid}")
    logger.info(f"✨ Generated Caption (link & UID): {caption}")

    # 💾 Save to Post History for DM matching
    history_file = "data/post_history.json"
    os.makedirs("data", exist_ok=True)
    history = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load history file: {e}")
    
    history[uid] = {
        "title": topic.title,
        "item_number": topic.item_number,
        "caption": caption,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_url": str(topic.source_meeting_url)
    }
    
    try:
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
        logger.info(f"💾 Saved UID {uid} to history.")
    except Exception as e:
        logger.error(f"Failed to save history: {e}")

    # ── 7. RENDER 3-SLIDE CAROUSEL ──
    renderer = SocialCardRenderer()
    uploader = ImgBBUploader()
    sourcer = ImageSource()

    img_keyword = ai_payload.get('img_keyword', 'Toronto City Hall')
    bg_image_url = sourcer.get_image_for_keyword(img_keyword)
    logger.info(f"📸 Sourced background for '{img_keyword}': {bg_image_url}")

    # Add subtitle for slide 1
    ai_payload['slide1_subtitle'] = f"{topic.item_number} — {topic.status or 'Pending'}"

    theme = "modern"
    title_text = f"{ai_payload.get('slide1_title', '')} {ai_payload.get('caption', '')}".lower()
    if any(kw in title_text for kw in ['urgent', 'emergency', 'slumlord', 'crackdown', 'warning', 'breaking', 'security']):
        theme = "emergency"

    slide_paths = await renderer.render_carousel(ai_payload, bg_image_url, theme)
    logger.info(f"🎨 Rendered {len(slide_paths)} carousel slides.")

    # ── 8. UPLOAD & POST ──
    public_urls = []
    for path in slide_paths:
        url = uploader.upload_image(path)
        if url: public_urls.append(url)

    if len(public_urls) >= 2:
        logger.info("Waiting 10 seconds for image propagation...")
        time.sleep(10)
        
        ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        IG_USER_ID = os.getenv('INSTAGRAM_USER_ID') or os.getenv('INSTAGRAM_ACCOUNT_ID')

        if ACCESS_TOKEN and IG_USER_ID:
            logger.info(f"📱 Posting {len(public_urls)}-slide carousel to Instagram...")
            post_carousel_to_instagram(ACCESS_TOKEN, IG_USER_ID, public_urls, caption)
        else:
            logger.warning("⚠️ Skipping Instagram post: Missing credentials.")
            for i, p in enumerate(slide_paths):
                logger.info(f"  Slide {i+1}: {p}")
    else:
        logger.error("❌ Failed to upload enough slides for a carousel.")


if __name__ == "__main__":
    asyncio.run(run_single_post_pipeline())
