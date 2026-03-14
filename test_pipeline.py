"""
Test pipeline for RAG-enhanced visuals.
Uses mock data to test the full flow without consuming AI credits.
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
from instagram_poster import post_photo_to_instagram
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def run_test_pipeline():
    """
    Tests the RAG-enhanced deep-dive flow with mock data.
    Simulates: ingestion → retrieval → focused post generation → rendering.
    """
    load_dotenv()
    logger.info("🧪 Launching RAG-Enhanced Visual Test...")

    # ── 1. Mock historical document ingestion ──
    vector_store = CivicVectorStore()

    # Simulate a past bylaw about housing enforcement
    historical_doc = """
    City of Toronto Bylaw 2024-0891: Residential Tenancies Enforcement Act.
    Council voted 25-2 to increase penalties for landlords who fail to maintain
    properties to minimum standards. The previous fine was $500 per infraction.
    This bylaw raised it to $10,000 per infraction. Councillor Jamaal Myers
    stated this would 'finally hold slumlords accountable.' However, enforcement
    was criticized as inadequate — only 12 inspectors for 300,000+ rental units.
    The Housing Secretariat budget was NOT increased alongside enforcement powers.
    """
    chunks = chunk_document(historical_doc, metadata={
        "source": "Bylaw-2024-0891",
        "title": "Residential Tenancies Enforcement Act",
        "doc_type": "bylaw"
    })
    vector_store.ingest(chunks)

    # ── 2. Mock today's agenda item (the "star") ──
    mock_topic = {
        "item_number": "2026.EX29.14",
        "title": "Expanding Rental Housing Enforcement Powers",
        "status": "Adopted",
        "summary": "City staff recommend expanding the Rental Housing Enforcement Unit "
                   "with 40 new inspectors and mandatory city-led repairs for buildings "
                   "that fail 3 consecutive inspections. Budget: $8.2M annually.",
        "recommendations": "1. Approve 40 additional housing inspectors. "
                          "2. Authorize city-led emergency repairs. "
                          "3. Fund from property tax levy increase of 0.3%.",
        "parsed_pdf_text": "The current enforcement regime has 12 inspectors covering "
                          "300,000+ rental units. Average response time for complaints "
                          "is 45 days. The proposed expansion would reduce this to 7 days."
    }

    # ── 3. Retrieve historical context ──
    search_query = f"{mock_topic['title']} {mock_topic['summary']}"
    historical_context = vector_store.search(search_query, k=3)
    logger.info(f"🔍 Retrieved {len(historical_context)} historical chunks.")
    for ctx in historical_context:
        logger.info(f"   Context from: {ctx['metadata'].get('source', 'unknown')} (distance: {ctx['distance']:.3f})")

    # ── 4. Mock AI output (what the deep-dive AI would produce) ──
    # In production, this comes from generate_deep_dive_post_async
    mock_ai_payload = {
        "caption": "Toronto just armed itself against slumlords — 40 new inspectors incoming. 🔨",
        "card_title": "THE SLUMLORD CRACKDOWN",
        "card_body": [
            "Council approved 40 new housing inspectors — response time drops from 45 to 7 days.",
            "Landlords who fail 3 inspections face mandatory city-led repairs at their expense.",
            "In 2024, fines were raised to $10K but only 12 inspectors existed. Now they're backing it up."
        ],
        "cta": "DM HOUSING for the full report",
        "img_keyword": "Toronto apartment building enforcement"
    }

    # ── 5. Render the editorial card ──
    renderer = SocialCardRenderer()
    sourcer = ImageSource()

    bg_image_url = sourcer.get_image_for_keyword(mock_ai_payload["img_keyword"])
    logger.info(f"📸 Sourced background: {bg_image_url}")

    image_path = await renderer.render_card(
        title=mock_ai_payload["card_title"],
        subtitle=f"{mock_topic['item_number']} — {mock_topic['status']}",
        body=mock_ai_payload["card_body"],
        cta=mock_ai_payload["cta"],
        bg_image=bg_image_url,
        filename=f"rag_test_{int(time.time())}.jpg",
        theme="emergency"
    )

    # ── 6. Upload & Post ──
    uploader = ImgBBUploader()
    public_image_url = uploader._upload_catbox(image_path)

    if not public_image_url:
        logger.error("❌ Hosting failed.")
        return

    logger.info("Waiting 10 seconds for image propagation...")
    time.sleep(10)

    ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    IG_USER_ID = os.getenv('INSTAGRAM_USER_ID')

    if ACCESS_TOKEN and IG_USER_ID:
        logger.info(f"📱 Posting to Instagram with URL: {public_image_url}")
        post_photo_to_instagram(ACCESS_TOKEN, IG_USER_ID, public_image_url, mock_ai_payload["caption"])
    else:
        logger.info(f"📋 Skipping Instagram (no credentials). Card saved at: {image_path}")


if __name__ == "__main__":
    asyncio.run(run_test_pipeline())
