import logging
import json
from scraper.downloader import PlaywrightDownloader
from scraper.parser import PDFParser

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    target_url = "https://www.toronto.ca/legdocs/bylaws/2026/law0061.pdf"
    
    logger.info("Initializing CivicClaw Scraper Pipeline...")
    
    # 1. Download
    downloader = PlaywrightDownloader(download_dir="downloads")
    try:
        pdf_path = downloader.download_pdf(target_url)
    except Exception as e:
        logger.error(f"Pipeline failed during download: {e}")
        return

    # 2. Parse
    parser = PDFParser()
    try:
        bylaw_doc = parser.parse_pdf(file_path=pdf_path, source_url=target_url)
    except Exception as e:
        logger.error(f"Pipeline failed during parsing: {e}")
        return

    # 3. Output
    logger.info("Pipeline Execution Successful. Extracted Document Info:")
    
    # Dump the Pydantic model to JSON for easy viewing
    output_json = bylaw_doc.model_dump_json(indent=2)
    print(output_json)
    
    # Optionally save the JSON output locally
    with open("downloads/output.json", "w", encoding="utf-8") as f:
        f.write(output_json)
    logger.info(f"Saved extracted data to downloads/output.json")

if __name__ == "__main__":
    main()
