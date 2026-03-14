import logging
import asyncio
import os
import sys

# Add src to sys.path so modules can be found
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from scraper.open_data import OpenDataClient
from scraper.tmmis import TMMISScraper
from scraper.bylaws_registry import BylawRegistryScraper
from ai.agent import CivicAIAgent
from social.instagram import InstagramClient
from instagram_poster import post_photo_to_instagram
from visuals.renderer import SocialCardRenderer
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
    
    # 4. Generate Structured AI Content
    ai_agent = CivicAIAgent()
    ai_payload = await ai_agent.generate_aggregate_post_async(meeting_data, bylaw_data, project_data)
    
    caption = ai_payload.get('caption', 'New Toronto updates! Check the card. 🏙️')
    logger.info(f"✨ Generated Short Caption: {caption}")
    
    # 5. Create Premium Visual Card
    from visuals.renderer import SocialCardRenderer
    from visuals.uploader import ImgBBUploader
    from visuals.source import ImageSource
    
    visual_renderer = SocialCardRenderer()
    uploader = ImgBBUploader()
    sourcer = ImageSource()
    
    # Extract data for card
    card_title = ai_payload.get('card_title', 'CIVIC ALERT').upper()
    card_subtitle = meeting_data.get('title', 'City Hall Update')
    card_body = ai_payload.get('card_body', ['Check DM for details.'])
    card_cta = ai_payload.get('cta', 'DM MINUTES for more')
    img_keyword = ai_payload.get('img_keyword', 'Toronto')

    # Choose a theme
    card_theme = "modern"
    if any(kw in card_title.lower() for kw in ['urgent', 'emergency', 'slumlord', 'warning']):
        card_theme = "emergency"

    # Source dynamic background
    bg_image_url = sourcer.get_image_for_keyword(img_keyword)
    logger.info(f"📸 Sourced dynamic background for '{img_keyword}': {bg_image_url}")

    card_filename = f"post_{int(asyncio.get_event_loop().time())}.jpg"
    image_path = await visual_renderer.render_card(
        title=card_title,
        subtitle=card_subtitle,
        body=card_body,
        cta=card_cta,
        bg_image=bg_image_url,
        filename=card_filename,
        theme=card_theme
    )

    # 6. Upload to ImgBB for public access (required by Instagram Graph API)
    public_image_url = uploader.upload_image(image_path)
    
    if public_image_url:
        logger.info("Waiting 10 seconds for image propagation...")
        import time
        time.sleep(10)

    # 7. Post to Instagram
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
