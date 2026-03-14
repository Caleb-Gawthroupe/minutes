"""
Test pipeline for carousel posting.
Uses mock data — no AI credits consumed.
"""
import logging
import asyncio
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from visuals.renderer import SocialCardRenderer
from visuals.uploader import ImgBBUploader
from visuals.source import ImageSource
from rag.vector_store import CivicVectorStore
from rag.chunker import chunk_document
from instagram_poster import post_carousel_to_instagram
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def run_test_pipeline():
    load_dotenv()
    logger.info("🧪 Launching Carousel Test Pipeline...")

    # ── 1. Ingest mock historical data ──
    vector_store = CivicVectorStore()
    historical_doc = """
    In 2024, Toronto City Council passed Bylaw 2024-0891, raising fines for
    non-compliant landlords from $500 to $10,000 per infraction. However, the
    Housing Secretariat budget was NOT increased — leaving only 12 inspectors
    for 300,000+ rental units. Advocates called it 'enforcement theatre.'
    """
    chunks = chunk_document(historical_doc, metadata={
        "source": "Bylaw-2024-0891", "title": "Tenancy Enforcement Act", "doc_type": "bylaw"
    })
    vector_store.ingest(chunks)

    # ── 2. Mock carousel AI payload (what the AI would produce) ──
    mock_payload = {
        "caption": "Toronto just hired 40 housing inspectors to back up slumlord fines. 🔨 Swipe for the full story.",
        "slide1_label": "The Decision",
        "slide1_title": "THE SLUMLORD CRACKDOWN",
        "slide1_subtitle": "2026.EX29.14 — Adopted",
        "slide1_summary": "Council approved 40 new housing inspectors and authorized mandatory city-led repairs for buildings that fail 3 consecutive inspections.",
        "slide2_label": "The Hard Stats",
        "slide2_title": "BY THE NUMBERS",
        "slide2_stats": [
            "Complaint response time drops from 45 days to just 7 days.",
            "Landlords who fail 3 inspections face city-led repairs at their expense.",
            "Funded by a 0.3% property tax levy — about $18/year for the average home."
        ],
        "slide3_label": "What This Means",
        "slide3_title": "YOUR RENT & REPAIRS",
        "slide3_body": "If you rent in a building with a history of code violations, expect to see inspectors much faster. If your landlord ignores repair orders 3 times, the city will step in, fix the issue, and bill the landlord directly.",
        "cta": "DM HOUSING for the full report",
        "img_keyword": "Toronto apartment building inspection"
    }

    # ── 3. Render 3-slide carousel ──
    renderer = SocialCardRenderer()
    sourcer = ImageSource()

    bg_image_url = sourcer.get_image_for_keyword(mock_payload["img_keyword"])
    logger.info(f"📸 Sourced background: {bg_image_url}")

    slide_paths = await renderer.render_carousel(mock_payload, bg_image_url, theme="emergency")
    logger.info(f"🎨 Rendered {len(slide_paths)} slides.")

    # ── 4. Upload all slides ──
    uploader = ImgBBUploader()
    public_urls = []
    for path in slide_paths:
        url = uploader._upload_catbox(path)
        if url:
            public_urls.append(url)
            logger.info(f"  Uploaded: {url}")

    if len(public_urls) < 2:
        logger.error("❌ Upload failed.")
        return

    logger.info("Waiting 10 seconds for propagation...")
    time.sleep(10)

    # ── 5. Post carousel ──
    ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    IG_USER_ID = os.getenv('INSTAGRAM_USER_ID')

    if ACCESS_TOKEN and IG_USER_ID:
        logger.info(f"📱 Posting {len(public_urls)}-slide carousel...")
        post_carousel_to_instagram(ACCESS_TOKEN, IG_USER_ID, public_urls, mock_payload["caption"])
    else:
        logger.info("📋 Skipping Instagram (no creds). Slides saved locally.")
        for i, p in enumerate(slide_paths):
            logger.info(f"  Slide {i+1}: {p}")


if __name__ == "__main__":
    asyncio.run(run_test_pipeline())
