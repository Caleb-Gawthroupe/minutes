import logging
import json
import os
from scraper.open_data import OpenDataClient
from scraper.tmmis import TMMISScraper
from scraper.bylaws_registry import BylawRegistryScraper

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_phase_2_pipeline():
    logger.info("Initializing CivicClaw Phase 2 Scraper Pipeline...")
    
    # 1. Open Data Polling
    open_data = OpenDataClient()
    notices = open_data.fetch_recent_notices()
    
    if not notices:
         logger.info("No notices found today. Exiting.")
         return

    logger.info(f"Found {len(notices)} notices. Moving to process deep context.")
    
    # 2. TMMIS Deep Context (REST API Bypass)
    # Using the undocumented REST APIs discovered to pull clean JSON agenda items
    tmmis = TMMISScraper(download_dir="downloads/tmmis")
    
    # For the simulation/demo, we search for 'housing' related items
    search_keyword = "housing"
    logger.info(f"Fetching recent TMMIS agenda items related to '{search_keyword}'...")
    
    # Note: This uses xvfb-run under the hood if run via the provided CLI 
    # but the class itself handles the Playwright handshake.
    items = tmmis.fetch_agenda_items(search_keyword)
    
    if items:
        logger.info(f"Successfully retrieved {len(items)} structured agenda items from TMMIS.")
    else:
        logger.warning("No TMMIS items found for the given keyword.")

    # 3. Bylaw Registry Polling (The Final Word)
    # As a demonstration of closing the loop, we check the registry for a known proposal/bylaw 
    bylaw_scraper = BylawRegistryScraper(download_dir="downloads/bylaws")
    
    # Simulating a check for a proposal that became By-law 61 in 2026
    demo_year = 2026
    demo_bylaw = "61"
    
    logger.info(f"Polling Registry for Year {demo_year}, Bylaw {demo_bylaw}...")
    final_bylaw_doc = bylaw_scraper.check_bylaw_status(demo_year, demo_bylaw)
    
    if final_bylaw_doc:
         logger.info(f"Bylaw Pipeline Complete! Found Final Law: {final_bylaw_doc.metadata.title}")

    # Output some results
    os.makedirs("downloads", exist_ok=True)
    results = {
        "notices": [n.model_dump() for n in notices[:5]],
        "tmmis_items": [i.model_dump() for i in items[:5]] if items else []
    }
    
    with open("downloads/pipeline_output.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
        logger.info("Saved pipeline results to downloads/pipeline_output.json")

if __name__ == "__main__":
    run_phase_2_pipeline()

