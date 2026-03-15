import logging
import asyncio
import os
import sys
import time
import json
import random
import string
import re
from dotenv import load_dotenv

# Add src to sys.path so modules can be found
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_single_topic(item, vector_store, ai_agent, renderer, uploader, sourcer, history, history_file):
    """Processes a single agenda item into a social media post."""
    topic_data = item.model_dump()
    logger.info(f"👉 Processing: '{item.title}' ({item.item_number})")

    # 1. RETRIEVE CONTEXT
    search_query = f"{item.title} {item.summary or ''}"
    context = vector_store.search(search_query, k=8)
    
    # 2. AI GENERATION
    ai_payload = await ai_agent.generate_deep_dive_post_async(topic_data, context)
    caption = ai_payload.get('caption', 'Civic Update! Swipe for details. 🏙️')
    
    if item.source_meeting_url:
        caption += f"\n\n🔗 Source: {item.source_meeting_url}"
    
    # Generate Unique Identifier (UID)
    clean_title = re.sub(r'[^A-Za-z]', '', item.title).upper()
    prefix = clean_title[:4] if len(clean_title) >= 4 else "MMIS"
    suffix = ''.join(random.choices(string.digits, k=2))
    uid = f"{prefix}{suffix}"
    
    caption += f"\n\n💬 DM us \"{uid}\" for the full report!"
    logger.info(f"✨ Created UID: {uid}")

    # 3. SAVE TO SUPABASE
    from supabase import create_client, Client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if url and key:
        try:
            sb: Client = create_client(url, key)
            sb.table("posts").upsert({
                "uid": uid,
                "title": item.title,
                "item_number": item.item_number,
                "caption": caption,
                "source_url": str(item.source_meeting_url),
                "timestamp": "now()"
            }).execute()
            logger.info(f"💾 Saved {uid} to Supabase.")
        except Exception as e:
            logger.error(f"Failed to save {uid} to Supabase: {e}")
    
    # 3b. (Legacy fallback) Save to History
    history[uid] = {
        "title": item.title,
        "item_number": item.item_number,
        "caption": caption,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_url": str(item.source_meeting_url)
    }

    # 4. RENDER & UPLOAD
    img_keyword = ai_payload.get('img_keyword', 'Toronto')
    bg_image_url = sourcer.get_image_for_keyword(img_keyword)
    
    ai_payload['slide1_subtitle'] = f"{item.item_number} — {item.status or 'Pending'}"
    
    theme = "modern"
    if any(kw in (ai_payload.get('slide1_title', '') + caption).lower() for kw in ['urgent', 'emergency', 'warning', 'breaking']):
        theme = "emergency"

    slide_paths = await renderer.render_carousel(ai_payload, bg_image_url, theme)
    
    public_urls = []
    for path in slide_paths:
        url = uploader.upload_image(path)
        if url: public_urls.append(url)

    # 5. POST TO INSTAGRAM
    if len(public_urls) >= 2:
        ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        IG_USER_ID = os.getenv('INSTAGRAM_USER_ID') or os.getenv('INSTAGRAM_ACCOUNT_ID')
        
        if ACCESS_TOKEN and IG_USER_ID:
            logger.info(f"📱 Posting carousel for {uid}...")
            post_carousel_to_instagram(ACCESS_TOKEN, IG_USER_ID, public_urls, caption)
            return True
    
    return False

async def run_multi_post_pipeline():
    load_dotenv()
    logger.info("🚀 Starting Multi-Post Batch Pipeline (Latest Items)...")

    # 1. SCRAPE LATEST
    tmmis = TMMISScraper(download_dir="downloads/tmmis")
    items = await tmmis.fetch_agenda_items_async("") 
    
    if not items:
        logger.error("❌ No items found.")
        return

    # 2. INITIALIZE SHARED COMPONENTS
    ai_agent = CivicAIAgent()
    renderer = SocialCardRenderer()
    uploader = ImgBBUploader()
    sourcer = ImageSource()
    vector_store = CivicVectorStore()
    
    # Supabase setup
    from supabase import create_client, Client
    sb_url = os.getenv("SUPABASE_URL")
    sb_key = os.getenv("SUPABASE_SERVICE_KEY")
    sb: Client = create_client(sb_url, sb_key)

    # 3. INGEST ALL INTO VECTOR STORE
    total_new = 0
    for item in items:
        text = f"{item.summary or ''} {item.recommendations or ''} {item.parsed_pdf_text or ''}"
        if text.strip():
            chunks = chunk_document(text, metadata={"source": item.item_number})
            total_new += vector_store.ingest(chunks)
    logger.info(f"🗄️ Ingested {total_new} new chunks for context.")

    # 4. SELECT TOP 5
    top_items = select_top_topic(items, top_n=5)
    
    # 5. LOOP AND PROCESS
    for i, item in enumerate(top_items):
        if i > 0:
            logger.info("⏳ Waiting 60s for rate-limiting...")
            await asyncio.sleep(60)
            
        success = await process_single_topic(
            item, vector_store, ai_agent, renderer, uploader, sourcer, {}, ""
        )
        
        if success:
            logger.info(f"✅ Post {i+1}/{len(top_items)} successful.")
        else:
            logger.error(f"❌ Post {i+1}/{len(top_items)} failed.")

if __name__ == "__main__":
    asyncio.run(run_multi_post_pipeline())
