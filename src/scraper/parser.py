import os
from pypdf import PdfReader
from .models import BylawDocument, DocumentMetadata
import logging

logger = logging.getLogger(__name__)

class PDFParser:
    def __init__(self):
        pass

    def parse_pdf(self, file_path: str, source_url: str) -> BylawDocument:
        """
        Parses a PDF file from the local path and returns a structured BylawDocument.
        """
        if not os.path.exists(file_path):
             raise FileNotFoundError(f"PDF file not found at {file_path}")

        logger.info(f"Parsing PDF document: {file_path}")
        
        try:
            reader = PdfReader(file_path)
            
            # Extract Text
            raw_text = ""
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    raw_text += page_text + "\n"
            
            # Extract Metadata
            meta = reader.metadata
            page_count = len(reader.pages)
            
            # PyPDF metadata parsing 
            doc_meta = DocumentMetadata(
                title=meta.title if meta else None,
                author=meta.author if meta else None,
                # Note: creation date parsing from PDF info format might be needed
                page_count=page_count
            )
            
            # Build the full document model
            bylaw_doc = BylawDocument(
                source_url=source_url,
                filename=os.path.basename(file_path),
                raw_text=raw_text.strip(),
                metadata=doc_meta
            )
            
            logger.info(f"Successfully parsed {file_path}: {page_count} pages extracted.")
            return bylaw_doc
            
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise e

if __name__ == "__main__":
    # Small test wrapper if running standalone on an existing file
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        parser = PDFParser()
        doc = parser.parse_pdf(test_file, source_url="test://local")
        print(f"Parsed text snippet ({len(doc.raw_text)} chars):")
        print(doc.raw_text[:500] + "...")
