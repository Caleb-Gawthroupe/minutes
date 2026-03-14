import asyncio
import os
import logging
from typing import List, Optional, Dict, Any
from playwright.async_api import async_playwright
import fitz  # PyMuPDF

from .models import Meeting, AgendaItem
from .downloader import PlaywrightDownloader

logger = logging.getLogger(__name__)

class TMMISScraper:
    """Scrapes meeting data from the Toronto Meeting Management Information System (TMMIS) via internal REST APIs."""
    
    BASE_URL = "https://secure.toronto.ca/council/"
    SEARCH_API = "https://secure.toronto.ca/council/api/multiple/agenda-items.json?pageNumber=0&pageSize=5&sortOrder=meetingDate desc,referenceSort"
    
    def __init__(self, download_dir: str = "downloads/tmmis"):
        self.download_dir = download_dir
        self.downloader = PlaywrightDownloader(download_dir=self.download_dir)
        os.makedirs(self.download_dir, exist_ok=True)

    def _parse_pdf_text_with_pymupdf(self, pdf_path: str) -> str:
        """Extract text from complex PDFs like staff reports using PyMuPDF."""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for i, page in enumerate(doc):
                text += page.get_text() + "\n"
            doc.close()
            return text
        except Exception as e:
            logger.error(f"PyMuPDF failed to parse {pdf_path}: {e}")
            return ""

    async def fetch_agenda_items_async(self, search_word: str) -> List[AgendaItem]:
        """Uses Playwright to handshake cookies and fetch structured JSON agendas."""
        items = []
        async with async_playwright() as p:
             # Use headless mode by default, check env 
             is_headless = os.getenv("HEADLESS", "true").lower() == "true"
             browser = await p.chromium.launch(
                 headless=is_headless, 
                 args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
             )
             context = await browser.new_context(
                 user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
             )
             page = await context.new_page()
             
             try:
                 logger.info(f"Navigating to {self.BASE_URL} to handshake cookies...")
                 # Go to the main page to get the XSRF-TOKEN
                 response = await page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
                 
                 # Wait a moment for cookies to settle
                 await asyncio.sleep(2)
                 
                 cookies = await context.cookies()
                 xsrf_token = next((c['value'] for c in cookies if c['name'] == 'XSRF-TOKEN'), None)
                 
                 if not xsrf_token:
                     logger.warning("Failed to retrieve XSRF-TOKEN cookie. API requests may fail.")
                 else:
                     logger.info("Successfully retrieved XSRF-TOKEN.")
                 
                 headers = {
                     "Accept": "application/json, text/plain, */*",
                     "Content-Type": "application/json",
                     "x-xsrf-token": xsrf_token if xsrf_token else ""
                 }
                 
                 payload = {
                     "includeTitle": True,
                     "includeSummary": True,
                     "includeRecommendations": True,
                     "includeDecisions": True,
                     "decisionBodyId": None,
                     "meetingFromDate": None,
                     "meetingToDate": None,
                     "word": search_word
                 }
                 
                 logger.info("Querying TMMIS REST API for agenda items...")
                 api_response = await context.request.post(
                     self.SEARCH_API,
                     headers=headers,
                     data=payload
                 )
                 
                 if not api_response.ok:
                     logger.error(f"API request failed with status: {api_response.status} {api_response.status_text}")
                     return items
                     
                 data = await api_response.json()
                 
                 logger.info("Successfully received API response.")
                 
                 # The 'Search' response returns records under the 'Records' key
                 results = data.get('Records', [])
                 if not results and isinstance(data, list):
                     results = data
                         
                 for item in results:
                     # Attempt to extract PDF links if backgroundAttachmentId exists
                     pdf_links = []
                     background_ids = item.get("backgroundAttachmentId", [])
                     
                     # Ensure we handle both lists and comma-separated strings if they occur
                     id_list = []
                     if isinstance(background_ids, list):
                         id_list = background_ids
                     elif isinstance(background_ids, str):
                         id_list = [id.strip() for id in background_ids.split(",") if id.strip()]
                     
                     for b_id in id_list:
                         # We need the agendaCd or year. Usually year is in the meetingDate.
                         year = "2026" 
                         meeting_ts = item.get("meetingDate")
                         if meeting_ts:
                             from datetime import datetime
                             year = str(datetime.fromtimestamp(meeting_ts / 1000).year)
                         
                         # committee code MUST be lowercase for the URL to work
                         agenda_cd = str(item.get("agendaCd", "Unknown")).lower()
                         if agenda_cd != "unknown":
                             pdf_url = f"https://www.toronto.ca/legdocs/mmis/{year}/{agenda_cd}/bgrd/backgroundfile-{b_id}.pdf"
                             pdf_links.append(pdf_url)

                     agenda_item = AgendaItem(
                         item_number=item.get("reference", "Unknown"),
                         title=item.get("agendaItemTitle", ""),
                         status=item.get("itemStatus", "Proposed"),
                         summary=item.get("agendaItemSummary"),
                         recommendations=item.get("agendaItemRecommendation"),
                         pdf_links=pdf_links
                     )
                     
                     # Extract PDF text if links exist
                     if pdf_links:
                         logger.info(f"Downloading and parsing {len(pdf_links)} report(s) for item {agenda_item.item_number}")
                         parsed_texts = []
                         import requests
                         for link in pdf_links:
                             try:
                                 # Faster than launching a browser for every file
                                 filename = os.path.basename(link)
                                 pdf_path = os.path.join(self.download_dir, filename)
                                 
                                 if not os.path.exists(pdf_path):
                                     r = requests.get(link, timeout=10)
                                     if r.status_code == 200:
                                         with open(pdf_path, "wb") as f:
                                             f.write(r.content)
                                     else:
                                         logger.warning(f"Failed to download PDF {link}: {r.status_code}")
                                         continue
                                 
                                 text = self._parse_pdf_text_with_pymupdf(pdf_path)
                                 if text:
                                     parsed_texts.append(text)
                             except Exception as e:
                                 logger.warning(f"Failed to fetch/parse PDF {link}: {e}")
                         
                         if parsed_texts:
                             agenda_item.parsed_pdf_text = "\n--- NEXT REPORT ---\n".join(parsed_texts)
                     
                     items.append(agenda_item)
                     
                 logger.info(f"Successfully mapped {len(items)} agenda items via REST API.")
                 return items
                 
             except Exception as e:
                  logger.error(f"Failed to scrape TMMIS APIs: {e}")
                  return items
             finally:
                  await browser.close()

    def fetch_agenda_items(self, search_word: str) -> List[AgendaItem]:
        return asyncio.run(self.fetch_agenda_items_async(search_word))


if __name__ == "__main__":
    # Test Execution
    logging.basicConfig(level=logging.INFO)
    scraper = TMMISScraper()
    items = scraper.fetch_agenda_items("housing")
    if items:
        # Print the first item
        print("First Item Parsed:")
        print(items[0].model_dump_json(indent=2))
    else:
        print("No items found or API failed.")
        
