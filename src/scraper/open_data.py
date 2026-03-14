import requests
import logging
from typing import List
from datetime import datetime
from .models import Notice

logger = logging.getLogger(__name__)

class OpenDataClient:
    """Client for interacting with the Toronto Open Data CKAN API."""
    
    # Direct downloading the JSON resource file 
    BASE_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/3bfab808-105b-45ab-8d92-cf1916594653/resource/5807d7d8-0d7b-44a7-a433-bbf8cc343963/download/meeting-schedule-all-committees-2022-2026.json"
    
    def __init__(self):
        pass

    def fetch_recent_notices(self, limit: int = 10) -> List[Notice]:
        """
        Fetches the latest meeting schedules from CKAN JSON file and parses them into Pydantic models.
        """
        logger.info(f"Fetching public notices from open.toronto.ca CKAN remote file")
        
        try:
            headers = {
                "User-Agent": "CivicClaw-Bot/1.0"
            }
            response = requests.get(self.BASE_URL, headers=headers, timeout=10)
            response.raise_for_status()
            records = response.json()
            
            notices = []
            
            # The JSON file is directly a list of records
            for item in records[:limit]:
                # Example record:
                # {"_id": 1, "Term": "2022-2026", "Committee": "Aboriginal Affairs Advisory Committee", 
                #  "MTG #": "1", "Date": "2024-10-08", "Start Time": "09:30 AM", "End Time": "18:00 PM"}
                
                # Attempt to parse date string 
                date_str = item.get("Date")
                parsed_date = None
                if date_str:
                     try:
                         # Dates in CKAN seem to be YYYY-MM-DD
                         parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                     except ValueError:
                         logger.warning(f"Could not parse date: {date_str}")

                # Since CKAN schedule doesn't explicitly guarantee a "meeting_id" mapping directly to TMMIS URLs easily
                # in this specific dataset without deep inspection, we map what we can.
                notice = Notice(
                    id=str(item.get("_id", "unknown")),
                    title=f"{item.get('Committee', 'Unknown Committee')} - Meeting {item.get('MTG #', '')}",
                    notice_type="Scheduled Meeting",
                    post_date=parsed_date,
                    meeting_id=None, # Needs a more complex cross-reference table to hit TMMIS later if possible
                    url=None
                )
                notices.append(notice)
                
            logger.info(f"Successfully parsed {len(notices)} structured meeting notices from CKAN.")
            return notices
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch data from Open Data CKAN API: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing Open Data CKAN API: {e}")
            return []

if __name__ == "__main__":
    # Test execution
    logging.basicConfig(level=logging.INFO)
    client = OpenDataClient()
    notices = client.fetch_recent_notices(limit=2)
    
    if notices:
        print(f"Sample CKAN Notice:\n{notices[0].model_dump_json(indent=2)}")
    else:
        print("No notices found or API structure needs adjustment.")
