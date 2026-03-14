import requests
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class ImageSource:
    """Helper to fetch relevant background images from Pexels/Unsplash."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PEXELS_API_KEY")
        self.search_url = "https://api.pexels.com/v1/search"
        
        # Internal fallbacks for common civic keywords if API fails or is missing
        self.stock_photos = {
            "mayor": "https://images.pexels.com/photos/1103970/pexels-photo-1103970.jpeg",
            "city_hall": "https://images.pexels.com/photos/374870/pexels-photo-374870.jpeg",
            "housing": "https://images.pexels.com/photos/439391/pexels-photo-439391.jpeg",
            "transit": "https://images.pexels.com/photos/1638218/pexels-photo-1638218.jpeg",
            "default": "https://images.pexels.com/photos/2093323/pexels-photo-2093323.jpeg" # Toronto Skyline
        }

    def get_image_for_keyword(self, keyword: str) -> str:
        """
        Fetches a high-quality photo from Pexels using the provided keyword.
        Falls back to internal stock library if API fails.
        """
        if self.api_key:
            try:
                # Sanitize and ground the query in a civic context
                grounded_query = f"{keyword} Toronto City Council"
                logger.info(f"🔍 Searching Pexels for grounded query: '{grounded_query}'")
                headers = {"Authorization": self.api_key}
                params = {"query": grounded_query, "per_page": 1, "orientation": "square"}
                response = requests.get(self.search_url, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                photos = data.get("photos", [])
                if photos:
                    # Prefer large/original for high-density rendering
                    img_url = photos[0].get("src", {}).get("large") or photos[0].get("src", {}).get("original")
                    if img_url:
                        logger.info(f"✅ Found Pexels image: {img_url}")
                        return img_url
            except Exception as e:
                logger.error(f"Pexels search failed for '{keyword}': {e}")

        # Intelligent mapping fallback
        k = keyword.lower()
        if any(w in k for w in ['chow', 'mayor', 'olivia']): return self.stock_photos['mayor']
        if any(w in k for w in ['hall', 'council', 'meeting']): return self.stock_photos['city_hall']
        if any(w in k for w in ['rent', 'tenant', 'building', 'home', 'houses']): return self.stock_photos['housing']
        if any(w in k for w in ['transit', 'ttc', 'bus', 'streetcar', 'subway']): return self.stock_photos['transit']
        
        return self.stock_photos['default']
