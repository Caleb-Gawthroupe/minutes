import logging
from typing import Optional
from .models import BylawDocument
from .downloader import PlaywrightDownloader
from .parser import PDFParser

logger = logging.getLogger(__name__)

class BylawRegistryScraper:
    """Scrapes finalized bylaws from the City of Toronto Bylaw list."""
    
    # E.g. https://www.toronto.ca/legdocs/bylaws/2026/law0061.pdf
    BASE_REGISTRY_URL = "https://www.toronto.ca/legdocs/bylaws/"
    
    def __init__(self, download_dir: str = "downloads/bylaws"):
        self.download_dir = download_dir
        self.downloader = PlaywrightDownloader(download_dir=self.download_dir)
        self.parser = PDFParser()

    async def check_bylaw_status_async(self, year: int, bylaw_number: str) -> Optional[BylawDocument]:
        """Async version of check_bylaw_status."""
        padded_number = str(bylaw_number).zfill(4) 
        target_url = f"{self.BASE_REGISTRY_URL}{year}/law{padded_number}.pdf"
        
        logger.info(f"Checking registry for bylaw: {target_url}")
        
        try:
            pdf_path = await self.downloader.download_pdf_async(target_url)
            bylaw_doc = self.parser.parse_pdf(file_path=pdf_path, source_url=target_url)
            logger.info(f"Successfully matched and parsed finalized bylaw: {bylaw_number}")
            return bylaw_doc
        except Exception as e:
            logger.info(f"Bylaw {year}-{bylaw_number} not yet found in registry or failed to download. ({e})")
            return None

    def check_bylaw_status(self, year: int, bylaw_number: str) -> Optional[BylawDocument]:
        import asyncio
        return asyncio.run(self.check_bylaw_status_async(year, bylaw_number))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    registry = BylawRegistryScraper()
    # Test with the known Phase 1 bylaw
    doc = registry.check_bylaw_status(2026, "61")
    if doc:
        print(f"Verified Final Bylaw: {doc.metadata.title}")
