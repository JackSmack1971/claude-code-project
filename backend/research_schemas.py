"""
Pydantic schemas for research assistant functionality.
Defines models for academic papers, citations, and search queries.
"""
from typing import Optional, List
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, HttpUrl, Field


class PaperSource(str, Enum):
    """Available academic paper sources."""
    ARXIV = "arxiv"
    PUBMED = "pubmed"
    WEB = "web"


class CitationFormat(str, Enum):
    """Supported citation formats."""
    BIBTEX = "bibtex"
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"


class PaperResult(BaseModel):
    """
    Structured representation of an academic paper.

    Compatible with ArXiv, PubMed, and scraped papers.
    """
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    abstract: Optional[str] = Field(None, description="Paper abstract/summary")
    url: str = Field(..., description="Direct link to paper")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    published_date: Optional[str] = Field(None, description="Publication date (YYYY-MM-DD or ISO format)")
    journal: Optional[str] = Field(None, description="Journal or publication venue")
    source: PaperSource = Field(..., description="Source of the paper (arxiv, pubmed, web)")
    pdf_url: Optional[str] = Field(None, description="Direct PDF link if available")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Attention Is All You Need",
                "authors": ["Ashish Vaswani", "Noam Shazeer"],
                "abstract": "The dominant sequence transduction models...",
                "url": "https://arxiv.org/abs/1706.03762",
                "doi": "10.48550/arXiv.1706.03762",
                "published_date": "2017-06-12",
                "journal": "NeurIPS 2017",
                "source": "arxiv",
                "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf"
            }
        }


class SearchQuery(BaseModel):
    """Query parameters for academic paper search."""
    query: str = Field(..., min_length=1, description="Search query string")
    max_results: int = Field(10, ge=1, le=100, description="Maximum number of results to return")
    source: Optional[PaperSource] = Field(None, description="Specific source to search (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "machine learning transformers",
                "max_results": 20,
                "source": "arxiv"
            }
        }


class ScrapeRequest(BaseModel):
    """Request to scrape a webpage."""
    url: str = Field(..., description="URL to scrape")
    selector: Optional[str] = Field(None, description="Optional CSS selector to extract specific content")
    extract_links: bool = Field(False, description="Whether to extract all links from the page")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://arxiv.org/abs/1706.03762",
                "selector": "div.abstract",
                "extract_links": False
            }
        }


class ScrapeResult(BaseModel):
    """Result from web scraping operation."""
    url: str = Field(..., description="URL that was scraped")
    title: Optional[str] = Field(None, description="Page title")
    content: str = Field(..., description="Extracted text content")
    links: List[dict] = Field(default_factory=list, description="Extracted links if requested")
    metadata: dict = Field(default_factory=dict, description="Additional metadata (meta tags, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/paper",
                "title": "Research Paper Title",
                "content": "Full text of the article...",
                "links": [{"text": "PDF", "href": "https://example.com/paper.pdf"}],
                "metadata": {"description": "Paper description from meta tag"}
            }
        }


class CitationRequest(BaseModel):
    """Request to format a citation."""
    paper: PaperResult = Field(..., description="Paper to cite")
    format: CitationFormat = Field(CitationFormat.BIBTEX, description="Desired citation format")

    class Config:
        json_schema_extra = {
            "example": {
                "paper": {
                    "title": "Attention Is All You Need",
                    "authors": ["Vaswani et al."],
                    "url": "https://arxiv.org/abs/1706.03762",
                    "published_date": "2017",
                    "source": "arxiv"
                },
                "format": "bibtex"
            }
        }


class CitationResponse(BaseModel):
    """Formatted citation response."""
    citation: str = Field(..., description="Formatted citation string")
    format: CitationFormat = Field(..., description="Format used")

    class Config:
        json_schema_extra = {
            "example": {
                "citation": "@article{vaswani2017attention,\\n  title={Attention Is All You Need},\\n  author={Vaswani, Ashish and others},\\n  year={2017}\\n}",
                "format": "bibtex"
            }
        }


# Database models for saved citations
class SavedCitationCreate(BaseModel):
    """Schema for creating a saved citation."""
    paper_data: PaperResult = Field(..., description="Paper information")
    format: CitationFormat = Field(CitationFormat.BIBTEX, description="Preferred citation format")
    notes: Optional[str] = Field(None, description="User notes about the paper")


class SavedCitationRead(SavedCitationCreate):
    """Schema for reading a saved citation (includes ID and timestamp)."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
