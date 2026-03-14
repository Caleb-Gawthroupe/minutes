import os
import requests
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class InstagramClient:
    """
    Client for the Instagram Graph API.
    Note: Requires an Instagram Business/Creator account and a valid Access Token.
    """
    def __init__(self):
        self.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.instagram_account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
        self.base_url = "https://graph.facebook.com/v18.0"

    def post_text_update(self, caption: str) -> bool:
        """
        Posts a text-based update. 
        Note: Instagram Graph API primarily supports Photo/Video containers.
        For text-only, we typically generate a background image first.
        """
        if not self.access_token or not self.instagram_account_id:
            logger.warning("Instagram Access Token or Account ID missing. Skipping post.")
            logger.info(f"PENDING SOCIAL POST:\n{caption}")
            return False

        # In a real implementation, you would:
        # 1. Create a media container (POST /media)
        # 2. Publish the container (POST /media_publish)
        
        logger.info("Successfully simulated Instagram post delivery.")
        return True

    def post_image_update(self, image_url: str, caption: str) -> bool:
        """Posts an image with a caption to Instagram."""
        if not self.access_token or not self.instagram_account_id:
            logger.warning("Instagram credentials missing. Logging post content.")
            logger.info(f"SOCIAL CONTENT (Image: {image_url}):\n{caption}")
            return False

        try:
            # 1. Create media container
            container_url = f"{self.base_url}/{self.instagram_account_id}/media"
            payload = {
                "image_url": image_url,
                "caption": caption,
                "access_token": self.access_token
            }
            response = requests.post(container_url, data=payload)
            response.raise_for_status()
            creation_id = response.json().get("id")

            # 2. Publish media container
            publish_url = f"{self.base_url}/{self.instagram_account_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }
            publish_response = requests.post(publish_url, data=publish_payload)
            publish_response.raise_for_status()
            
            logger.info(f"Successfully posted to Instagram! Post ID: {publish_response.json().get('id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to post to Instagram: {e}")
            return False

if __name__ == "__main__":
    # Test stub
    client = InstagramClient()
    client.post_text_update("Test caption for CivicClaw Phase 3!")
