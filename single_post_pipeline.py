import logging
import asyncio
import os
from scraper.open_data import OpenDataClient
from scraper.tmmis import TMMISScraper
from scraper.bylaws_registry import BylawRegistryScraper
from ai.agent import CivicAIAgent
from social.instagram import InstagramClient
from instagram_poster import post_photo_to_instagram
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_single_post_pipeline():
    load_dotenv()
    logger.info("🚀 Starting Single Post Pipeline...")
    
    # 1. Fetch 1 Recent Meeting Notice
    open_data = OpenDataClient()
    notices = open_data.fetch_recent_notices(limit=1)
    meeting_data = notices[0].model_dump() if notices else {"title": "No recent meeting", "post_date": "N/A"}
    
    # 2. Fetch 1 Recent Project (Agenda Item)
    tmmis = TMMISScraper(download_dir="downloads/tmmis")
    # Using 'housing' as a keyword for the 'project'
    items = await tmmis.fetch_agenda_items_async("housing")
    project_data = items[0].model_dump() if items else {"title": "No recent project", "item_number": "N/A", "summary": "N/A"}
    
    # 3. Fetch 1 Recent Bylaw
    bylaw_scraper = BylawRegistryScraper(download_dir="downloads/bylaws")
    # Using the demo bylaw as the 'recent' one
    bylaw_doc = await bylaw_scraper.check_bylaw_status_async(2026, "61")
    bylaw_data = {
        "title": bylaw_doc.metadata.title if bylaw_doc else "Recent Bylaw Update",
        "source_url": str(bylaw_doc.source_url) if bylaw_doc else "https://www.toronto.ca/legdocs/bylaws/2026/law0061.pdf"
    }
    
    # 4. Generate AI Caption
    ai_agent = CivicAIAgent()
    caption = await ai_agent.generate_aggregate_post_async(meeting_data, bylaw_data, project_data)
    
    logger.info(f"✨ Generated Caption:\n{caption}")
    
    # 5. Post to Instagram
    # Image URL from instagram_poster.py as requested
    IMAGE_URL = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSGZdBKcNDO8hu-tnOjXH6X9wYUqNWyMSztzA&s'
    
    ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    IG_USER_ID = os.getenv('INSTAGRAM_ACCOUNT_ID') # Note: main script uses ACCOUNT_ID, poster uses IG_USER_ID
    
    if not IG_USER_ID:
        IG_USER_ID = os.getenv('INSTAGRAM_USER_ID') # Fallback to poster's naming

    if ACCESS_TOKEN and IG_USER_ID:
        logger.info("📱 Posting to Instagram...")
        post_photo_to_instagram(ACCESS_TOKEN, IG_USER_ID, IMAGE_URL, caption)
    else:
        logger.warning("⚠️ Skipping Instagram post: Missing credentials (INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_ACCOUNT_ID).")
        logger.info(f"CAPTION WOULD HAVE BEEN:\n{caption}")

if __name__ == "__main__":
    asyncio.run(run_single_post_pipeline())
