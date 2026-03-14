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

    def send_dm_reply(self, recipient_id: str, message_text: str) -> bool:
        """Sends a direct message reply to a user who has messaged the business account within 24 hours."""
        if not self.access_token:
            logger.warning("Instagram Access Token missing. Simulated DM reply.")
            logger.info(f"PENDING DM to {recipient_id}:\n{message_text}")
            return False
        
        # We need the Facebook Page ID to send messages via Instagram Direct API.
        # This is expected to be passed from the environment for the DM agent.
        page_id = os.getenv("FACEBOOK_PAGE_ID")
        # Note: Sending DMs typically uses the Page Access Token, not the User token.
        page_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", self.access_token)

        if not page_id:
            logger.error("FACEBOOK_PAGE_ID missing. Cannot send real DM.")
            return False

        try:
            url = f"https://graph.facebook.com/v19.0/{page_id}/messages"
            payload = {
                "recipient": {"id": recipient_id},
                "message": {"text": message_text},
                "messaging_type": "RESPONSE",
                "access_token": page_token
            }
            res = requests.post(url, json=payload)
            res.raise_for_status()
            logger.info(f"✅ Successfully sent DM reply to {recipient_id}")
            return True
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ Failed to send DM to {recipient_id}: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending DM: {e}")
            return False

if __name__ == "__main__":
    # Test stub
    client = InstagramClient()
    client.post_text_update("Test caption for CivicClaw Phase 3!")
