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
from instagram_poster import post_photo_to_instagram
from visuals.renderer import SocialCardRenderer
from visuals.uploader import ImgBBUploader
from visuals.source import ImageSource
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def run_single_post_pipeline():
    load_dotenv()
    logger.info("🚀 Starting RAG-Enhanced Single Post Pipeline...")

    # ──────────────────────────────────────────────
    # 1. SCRAPE: Fetch today's meeting data
    # ──────────────────────────────────────────────
    tmmis = TMMISScraper(download_dir="downloads/tmmis")
    items = await tmmis.fetch_agenda_items_async("housing")
    logger.info(f"📋 Scraped {len(items)} agenda items from TMMIS.")

    if not items:
        logger.error("❌ No agenda items found. Exiting.")
        return

    # Also fetch bylaw for additional context
    bylaw_scraper = BylawRegistryScraper(download_dir="downloads/bylaws")
    bylaw_doc = await bylaw_scraper.check_bylaw_status_async(2026, "61")

    # ──────────────────────────────────────────────
    # 2. INGEST: Store everything in the vector DB
    # ──────────────────────────────────────────────
    vector_store = CivicVectorStore()
    total_ingested = 0

    for item in items:
        # Ingest agenda item summary + recommendations
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

    # Ingest bylaw if available
    if bylaw_doc and bylaw_doc.raw_text:
        chunks = chunk_document(bylaw_doc.raw_text, metadata={
            "source": str(bylaw_doc.source_url),
            "title": bylaw_doc.metadata.title or "Bylaw",
            "doc_type": "bylaw"
        })
        total_ingested += vector_store.ingest(chunks)

    stats = vector_store.get_stats()
    logger.info(f"🗄️  Vector store: {stats['total_chunks']} total chunks ({total_ingested} new today)")

    # ──────────────────────────────────────────────
    # 3. SELECT: Pick the most impactful topic
    # ──────────────────────────────────────────────
    top_items = select_top_topic(items, top_n=1)
    topic = top_items[0]
    topic_data = topic.model_dump()
    logger.info(f"🎯 Top topic: '{topic.title}' ({topic.item_number})")

    # ──────────────────────────────────────────────
    # 4. RETRIEVE: Get historical context from RAG
    # ──────────────────────────────────────────────
    search_query = f"{topic.title} {topic.summary or ''}"
    historical_context = vector_store.search(search_query, k=5)
    logger.info(f"🔍 Retrieved {len(historical_context)} historical context chunks.")

    # ──────────────────────────────────────────────
    # 5. GENERATE: AI Deep-Dive (meeting-first + RAG)
    # ──────────────────────────────────────────────
    ai_agent = CivicAIAgent()
    ai_payload = await ai_agent.generate_deep_dive_post_async(topic_data, historical_context)

    caption = ai_payload.get('caption', 'New Toronto updates! Check the card. 🏙️')
    logger.info(f"✨ Generated Caption: {caption}")

    # ──────────────────────────────────────────────
    # 6. RENDER: Premium visual card
    # ──────────────────────────────────────────────
    visual_renderer = SocialCardRenderer()
    uploader = ImgBBUploader()
    sourcer = ImageSource()

    card_title = ai_payload.get('card_title', 'CIVIC ALERT').upper()
    card_subtitle = f"{topic.item_number} — {topic.status or 'Pending'}"
    card_body = ai_payload.get('card_body', ['Check DM for details.'])
    card_cta = ai_payload.get('cta', 'DM MINUTES for more')
    img_keyword = ai_payload.get('img_keyword', 'Toronto City Hall')

    card_theme = "modern"
    if any(kw in card_title.lower() for kw in ['urgent', 'emergency', 'slumlord', 'warning', 'crackdown']):
        card_theme = "emergency"

    bg_image_url = sourcer.get_image_for_keyword(img_keyword)
    logger.info(f"📸 Sourced dynamic background for '{img_keyword}': {bg_image_url}")

    card_filename = f"post_{int(time.time())}.jpg"
    image_path = await visual_renderer.render_card(
        title=card_title,
        subtitle=card_subtitle,
        body=card_body,
        cta=card_cta,
        bg_image=bg_image_url,
        filename=card_filename,
        theme=card_theme
    )

    # ──────────────────────────────────────────────
    # 7. UPLOAD & POST
    # ──────────────────────────────────────────────
    public_image_url = uploader.upload_image(image_path)

    if public_image_url:
        logger.info("Waiting 10 seconds for image propagation...")
        time.sleep(10)

    ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    IG_USER_ID = os.getenv('INSTAGRAM_USER_ID') or os.getenv('INSTAGRAM_ACCOUNT_ID')

    if ACCESS_TOKEN and IG_USER_ID and public_image_url:
        logger.info(f"🎨 Visual published at: {public_image_url}")
        logger.info("📱 Posting to Instagram...")
        post_photo_to_instagram(ACCESS_TOKEN, IG_USER_ID, public_image_url, caption)
    else:
        logger.warning("⚠️ Skipping Instagram post: Missing credentials or image hosting failed.")
        logger.info(f"STAGED CAPTION:\n{caption}")
        logger.info(f"LOCAL CARD: {image_path}")


if __name__ == "__main__":
    asyncio.run(run_single_post_pipeline())
