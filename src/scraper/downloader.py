import asyncio
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)

class PlaywrightDownloader:
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def _get_filename_from_url(self, url: str) -> str:
        """Extract the filename from the URL, or generate a default."""
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            filename = "document.pdf"
        return filename

    async def download_pdf_async(self, url: str) -> str:
        """Downloads a PDF from a given URL using Playwright."""
        filename = self._get_filename_from_url(url)
        file_path = os.path.join(self.download_dir, filename)

        logger.info(f"Attempting to download {url} to {file_path}")

        async with async_playwright() as p:
            # Using Chromium, headless mode
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # We expect a download to trigger when navigating to a PDF link
                async with page.expect_download() as download_info:
                    try:
                        await page.goto(url)
                    except Exception as e:
                        # Playwright throws an exception when navigation results in a download
                        if "Download is starting" not in str(e):
                            raise e

                download = await download_info.value
                
                # Save the download to our targeted directory
                await download.save_as(file_path)
                logger.info(f"Successfully downloaded: {file_path}")
                return file_path
                
            except Exception as e:
                logger.error(f"Failed to download PDF from {url}: {e}")
                raise e
            finally:
                await browser.close()

    def download_pdf(self, url: str) -> str:
         """Synchronous wrapper for download_pdf_async."""
         return asyncio.run(self.download_pdf_async(url))

if __name__ == "__main__":
    # Test execution
    downloader = PlaywrightDownloader()
    url = "https://www.toronto.ca/legdocs/bylaws/2026/law0061.pdf"
    file_path = downloader.download_pdf(url)
    print(f"Downloaded file to: {file_path}")
