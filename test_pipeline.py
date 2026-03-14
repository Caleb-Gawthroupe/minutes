import os
import asyncio
import logging
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from visuals.renderer import SocialCardRenderer
from visuals.uploader import ImgBBUploader
from visuals.source import ImageSource
from instagram_poster import post_photo_to_instagram

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_test_pipeline():
    """
    Tests the new 'Sleek Editorial' visual flow with dynamic images.
    """
    load_dotenv()
    logger.info("🧪 Launching Visual Upgrade Test...")

    # 1. Mock Data (Codex-Style)
    mock_payload = {
        "caption": "URGENT: Mayor Chow's new budget is out. Here is what it means for your commute. 🚇 #TorontoMinutes",
        "card_title": "THE CHOW BUDGET",
        "card_body": [
            "TTC fares frozen at current rates for the rest of 2026.",
            "City commits $40M to immediate pothole repair blitz.",
            "New property tax rebate for seniors confirmed."
        ],
        "cta": "DM BUDGET for the full report",
        "img_keyword": "Mayor Olivia Chow Toronto"
    }

    # 2. Source Image
    sourcer = ImageSource()
    bg_image_url = sourcer.get_image_for_keyword(mock_payload['img_keyword'])
    logger.info(f"📸 Sourced background: {bg_image_url}")

    # 3. Render Image
    renderer = SocialCardRenderer()
    card_filename = f"editorial_{int(asyncio.get_event_loop().time())}.jpg"
    image_path = await renderer.render_card(
        title=mock_payload['card_title'],
        subtitle="MUNICIPAL MONITOR",
        body=mock_payload['card_body'],
        cta=mock_payload['cta'],
        bg_image=bg_image_url,
        filename=card_filename,
        theme="modern"
    )

    # 4. Upload to Hosting (Forced Catbox for Meta compatibility)
    uploader = ImgBBUploader()
    public_image_url = uploader._upload_catbox(image_path)

    if not public_image_url:
        logger.error("❌ Hosting failed.")
        return

    # 4. Post to Instagram
    logger.info("Waiting 10 seconds for image propagation...")
    await asyncio.sleep(10)

    ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    IG_USER_ID = os.getenv('INSTAGRAM_USER_ID') or os.getenv('INSTAGRAM_ACCOUNT_ID')

    if ACCESS_TOKEN and IG_USER_ID:
        logger.info(f"📱 Posting to Instagram with URL: {public_image_url}")
        post_photo_to_instagram(ACCESS_TOKEN, IG_USER_ID, public_image_url, mock_payload['caption'])
    else:
        logger.warning("⚠️ Missing Instagram credentials in .env")

if __name__ == "__main__":
    asyncio.run(run_test_pipeline())
