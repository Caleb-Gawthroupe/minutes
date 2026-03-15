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

from datetime import datetime, timedelta

async def fetch_items_for_window(scraper, from_ms, to_ms):
    """Local helper to fetch items for a specific date window without changing tmmis.py."""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        # Re-using the handshake logic locally to support date filtering
        is_headless = os.getenv("HEADLESS", "false").lower() == "true"
        browser = await p.chromium.launch(headless=is_headless, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        page = await context.new_page()
        
        try:
            await page.goto(scraper.BASE_URL, wait_until="networkidle")
            await asyncio.sleep(2)
            cookies = await context.cookies()
            xsrf = next((c['value'] for c in cookies if c['name'] == 'XSRF-TOKEN'), None)
            
            data = await page.evaluate(f"""
                async (args) => {{
                    const res = await fetch(args.url, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json', 'x-xsrf-token': args.token }},
                        body: JSON.stringify({{
                            includeTitle: true, includeSummary: true, includeRecommendations: true, 
                            includeDecisions: true, meetingFromDate: args.from_date, meetingToDate: args.to_date, word: ""
                        }})
                    }});
                    return res.json();
                }}
            """, {"url": scraper.SEARCH_API, "token": xsrf or "", "from_date": from_ms, "to_date": to_ms})
            
            results = data.get('Records', [])
            items = []
            from scraper.models import AgendaItem
            for item in results:
                items.append(AgendaItem(
                    item_number=item.get("reference", "Unknown"),
                    title=item.get("agendaItemTitle", ""),
                    status=item.get("itemStatus", "Proposed"),
                    summary=item.get("agendaItemSummary"),
                    recommendations=item.get("agendaItemRecommendation"),
                    source_meeting_url=f"https://secure.toronto.ca/council/agenda-item.do?item={item.get('reference')}",
                    pdf_links=[] # Skipping PDFs for historical speed
                ))
            return items
        finally:
            await browser.close()

async def run_multi_post_pipeline():
    load_dotenv()
    logger.info("🚀 Starting Weekly Historical Pipeline...")

    # Initialize shared components
    scraper = TMMISScraper()
    ai_agent = CivicAIAgent()
    renderer = SocialCardRenderer()
    uploader = ImgBBUploader()
    sourcer = ImageSource()
    vector_store = CivicVectorStore()
    
    # Supabase setup
    from supabase import create_client, Client
    sb: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

    # 1. GENERATE 5 WEEKLY WINDOWS
    now = datetime.now()
    selected_items = []
    
    for i in range(5):
        # Window: [7*i days ago - 3 days, 7*i days ago + 3 days]
        center_date = now - timedelta(weeks=i)
        start_date = center_date - timedelta(days=3)
        end_date = center_date + timedelta(days=3)
        
        from_ms = int(start_date.timestamp() * 1000)
        to_ms = int(end_date.timestamp() * 1000)
        
        logger.info(f"📅 Fetching items for week {i} ({start_date.date()} to {end_date.date()})...")
        items = await fetch_items_for_window(scraper, from_ms, to_ms)
        
        if items:
            top = select_top_topic(items, top_n=1)
            if top:
                selected_items.append(top[0])
                logger.info(f"✅ Selected: {top[0].title[:50]}...")
        else:
            logger.warning(f"⚠️ No items found for window {i}")

    # 2. PROCESS THEM
    for i, item in enumerate(selected_items):
        if i > 0:
            logger.info("⏳ Waiting 60s for rate-limiting...")
            await asyncio.sleep(60)
            
        # Ingest for RAG context
        text = f"{item.summary or ''} {item.recommendations or ''}"
        vector_store.ingest(chunk_document(text, metadata={"source": item.item_number}))

        success = await process_single_topic(
            item, vector_store, ai_agent, renderer, uploader, sourcer, {}, ""
        )
        if success:
            logger.info(f"🎊 Post {i+1}/5 finished!")

if __name__ == "__main__":
    asyncio.run(run_multi_post_pipeline())
