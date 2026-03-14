import os
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ImgBBUploader:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("IMGBB_API_KEY")
        self.endpoint = "https://api.imgbb.com/1/upload"

    def upload_image(self, file_path: str, expiration: int = 600) -> Optional[str]:
        """
        Uploads an image. Tries Catbox first (vetted for Meta compatibility),
        shorter links, and high reliability. Falls back to ImgBB.
        """
        url = self._upload_catbox(file_path)
        if url: return url
        
        if self.api_key:
            return self._upload_imgbb(file_path, expiration)
            
        return None

    def _upload_imgbb(self, file_path: str, expiration: int) -> Optional[str]:
        try:
            with open(file_path, "rb") as file:
                payload = {"key": self.api_key, "expiration": expiration}
                files = {"image": file}
                logger.info(f"Uploading {file_path} to ImgBB...")
                response = requests.post(self.endpoint, params=payload, files=files)
                response.raise_for_status()
                data = response.json()
                
                # 'display_url' is often more stable for Meta's crawler than 'url'
                display_url = data.get("data", {}).get("display_url")
                direct_url = data.get("data", {}).get("url")
                
                final_link = display_url or direct_url
                if final_link:
                    logger.info(f"Successfully uploaded to ImgBB: {final_link}")
                    return final_link
        except Exception as e:
            logger.error(f"ImgBB upload failed: {e}")
            return None

    def _upload_catbox(self, file_path: str) -> Optional[str]:
        try:
            logger.info(f"Uploading {file_path} to Catbox...")
            with open(file_path, "rb") as f:
                response = requests.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": f}
                )
                response.raise_for_status()
                url = response.text.strip()
                if url.startswith("https://"):
                    logger.info(f"Successfully uploaded to Catbox: {url}")
                    return url
        except Exception as e:
            logger.error(f"Catbox upload failed: {e}")
        return None

if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    uploader = ImgBBUploader()
    # Replace with a real path if testing manually
    # url = uploader.upload_image("downloads/visuals/test_card.png")
    # print(f"Public URL: {url}")
