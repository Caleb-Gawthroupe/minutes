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


# --- Phase 2 Models: Total Data Scraping Flow ---

class Notice(BaseModel):
    """Represents a public notice pulled from the Toronto Open Data API."""
    id: str = Field(..., description="The unique identifier for the notice from the API.")
    title: str = Field(..., description="The title of the public notice.")
    notice_type: str = Field(default="", description="The category/type of the notice.")
    post_date: Optional[datetime] = Field(default=None, description="When the notice was published.")
    meeting_id: Optional[str] = Field(default=None, description="The associated TMMIS meeting ID, if any.")
    url: Optional[HttpUrl] = Field(default=None, description="Direct URL to the notice details.")


class AgendaItem(BaseModel):
    """Represents a specific item or motion on a meeting agenda."""
    item_number: str = Field(..., description="The alphanumeric designation (e.g., 'TE9.45').")
    title: str = Field(..., description="The title of the agenda item.")
    status: str = Field(default="", description="The status (e.g., 'Adopted', 'Deferred').")
    summary: Optional[str] = Field(default=None, description="Extracted 'Summary' or 'Background' of the item.")
    recommendations: Optional[str] = Field(default=None, description="Proposed recommendations text.")
    pdf_links: list[HttpUrl] = Field(default_factory=list, description="Links to attached PDFs (staff reports, etc).")
    parsed_pdf_text: Optional[str] = Field(default=None, description="Extracted text from attached PDFs using PyMuPDF.")
    
    # --- Phase 3: AI Intelligence ---
    ai_summary: Optional[str] = Field(default=None, description="AI-generated concise summary of the item.")
    social_post: Optional[str] = Field(default=None, description="AI-generated viral social media caption.")


class Meeting(BaseModel):
    """Represents a specific TMMIS meeting."""
    meeting_id: str = Field(..., description="The TMMIS meeting identifier.")
    committee_name: str = Field(default="", description="Name of the committee.")
    meeting_date: Optional[datetime] = Field(default=None, description="The date of the meeting.")
    agenda_items: list[AgendaItem] = Field(default_factory=list, description="The items discussed in this meeting.")