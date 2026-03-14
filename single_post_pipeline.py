import logging
import asyncio
import os
import sys
import time

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
    logger.info("🚀 Starting Carousel Pipeline...")

    # ── 1. SCRAPE ──
    tmmis = TMMISScraper(download_dir="downloads/tmmis")
    items = await tmmis.fetch_agenda_items_async("housing")
    logger.info(f"📋 Scraped {len(items)} agenda items from TMMIS.")

    if not items:
        logger.error("❌ No agenda items found. Exiting.")
        return

    bylaw_scraper = BylawRegistryScraper(download_dir="downloads/bylaws")
    bylaw_doc = await bylaw_scraper.check_bylaw_status_async(2026, "61")

    # ── 2. INGEST INTO VECTOR STORE ──
    vector_store = CivicVectorStore()
    total_ingested = 0

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
                "status": item.status or "unknown"
            })
            total_ingested += vector_store.ingest(chunks)

    if bylaw_doc and bylaw_doc.raw_text:
        chunks = chunk_document(bylaw_doc.raw_text, metadata={
            "source": str(bylaw_doc.source_url),
            "title": bylaw_doc.metadata.title or "Bylaw",
            "doc_type": "bylaw"
        })
        total_ingested += vector_store.ingest(chunks)

    stats = vector_store.get_stats()
    logger.info(f"🗄️  Vector store: {stats['total_chunks']} total chunks ({total_ingested} new)")

    # ── 3. SELECT TOP TOPIC ──
    top_items = select_top_topic(items, top_n=1)
    topic = top_items[0]
    topic_data = topic.model_dump()
    logger.info(f"🎯 Top topic: '{topic.title}' ({topic.item_number})")

    # ── 4. RETRIEVE HISTORICAL CONTEXT ──
    search_query = f"{topic.title} {topic.summary or ''}"
    historical_context = vector_store.search(search_query, k=5)
    logger.info(f"🔍 Retrieved {len(historical_context)} historical context chunks.")

    # ── 5. AI CAROUSEL GENERATION (1 call) ──
    ai_agent = CivicAIAgent()
    ai_payload = await ai_agent.generate_deep_dive_post_async(topic_data, historical_context)

    caption = ai_payload.get('caption', 'New from Toronto council! Swipe for details. 🏙️')
    logger.info(f"✨ Generated Caption: {caption}")

    # ── 6. RENDER 3-SLIDE CAROUSEL ──
    renderer = SocialCardRenderer()
    uploader = ImgBBUploader()
    sourcer = ImageSource()

    img_keyword = ai_payload.get('img_keyword', 'Toronto City Hall')
    bg_image_url = sourcer.get_image_for_keyword(img_keyword)
    logger.info(f"📸 Sourced background for '{img_keyword}': {bg_image_url}")

    # Add subtitle for slide 1
    ai_payload['slide1_subtitle'] = f"{topic.item_number} — {topic.status or 'Pending'}"

    theme = "modern"
    title = ai_payload.get('slide1_title', '').lower()
    if any(kw in title for kw in ['urgent', 'emergency', 'slumlord', 'crackdown', 'warning']):
        theme = "emergency"

    slide_paths = await renderer.render_carousel(ai_payload, bg_image_url, theme)
    logger.info(f"🎨 Rendered {len(slide_paths)} carousel slides.")

    # ── 7. UPLOAD ALL SLIDES ──
    public_urls = []
    for path in slide_paths:
        url = uploader.upload_image(path)
        if url:
            public_urls.append(url)
        else:
            logger.error(f"❌ Failed to upload slide: {path}")

    if len(public_urls) < 2:
        logger.error("❌ Need at least 2 uploaded slides for a carousel. Exiting.")
        return

    logger.info("Waiting 10 seconds for image propagation...")
    time.sleep(10)

    # ── 8. POST CAROUSEL ──
    ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    IG_USER_ID = os.getenv('INSTAGRAM_USER_ID') or os.getenv('INSTAGRAM_ACCOUNT_ID')

    if ACCESS_TOKEN and IG_USER_ID:
        logger.info(f"📱 Posting {len(public_urls)}-slide carousel to Instagram...")
        post_carousel_to_instagram(ACCESS_TOKEN, IG_USER_ID, public_urls, caption)
    else:
        logger.warning("⚠️ Skipping Instagram post: Missing credentials.")
        logger.info(f"STAGED CAPTION:\n{caption}")
        for i, p in enumerate(slide_paths):
            logger.info(f"  Slide {i+1}: {p}")


if __name__ == "__main__":
    asyncio.run(run_single_post_pipeline())
