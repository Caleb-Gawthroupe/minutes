from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field


class DocumentMetadata(BaseModel):
    """Metadata extracted from the PDF itself (e.g., via PyPDF)."""
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[datetime] = None
    page_count: int = 0


class BylawDocument(BaseModel):
    """Represents a scraped bylaw document and its extracted contents."""
    source_url: HttpUrl = Field(..., description="The original URL of the PDF document.")
    filename: str = Field(..., description="The local filename where the PDF is saved.")
    raw_text: str = Field(default="", description="The full extracted text content from the PDF.")
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata, description="Extracted PDF metadata.")
    
    # Future fields (e.g., Langchain summaries) can be added here
    # summary: Optional[str] = None
    # key_details: Optional[list[str]] = None