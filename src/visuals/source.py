import requests
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class ImageSource:
    """Helper to fetch relevant background images from Pexels/Unsplash."""
    
    def __init__(self, api_key: Optional[str] = None):
        # We'll use a public search approach for now, or fallback to themed city photos
        self.stock_photos = {
            "mayor": "https://images.pexels.com/photos/1103970/pexels-photo-1103970.jpeg",
            "city_hall": "https://images.pexels.com/photos/374870/pexels-photo-374870.jpeg",
            "housing": "https://images.pexels.com/photos/439391/pexels-photo-439391.jpeg",
            "transit": "https://images.pexels.com/photos/1638218/pexels-photo-1638218.jpeg",
            "default": "https://images.pexels.com/photos/2093323/pexels-photo-2093323.jpeg" # Toronto Skyline
        }

    def get_image_for_keyword(self, keyword: str) -> str:
        """
        Intelligently maps keywords to a high-quality stock photo. 
        In a real app, this could call Pexels API.
        """
        k = keyword.lower()
        if any(w in k for w in ['chow', 'mayor', 'olivia']): return self.stock_photos['mayor']
        if any(w in k for w in ['hall', 'council', 'meeting']): return self.stock_photos['city_hall']
        if any(w in k for w in ['rent', 'tenant', 'building', 'home']): return self.stock_photos['housing']
        if any(w in k for w in ['transit', 'ttc', 'bus', 'streetcar']): return self.stock_photos['transit']
        
        return self.stock_photos['default']
