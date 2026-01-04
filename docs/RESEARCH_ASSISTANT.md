# Research Assistant Documentation

## Overview

The Research Assistant feature provides academic paper search, web scraping, and citation management capabilities to AgentFactory.

## Features

### 1. Academic Paper Search

#### ArXiv Search
Search the ArXiv preprint repository for physics, mathematics, and computer science papers.

**API Endpoint:** `POST /research/arxiv`

**Request:**
```json
{
  "query": "machine learning",
  "max_results": 10
}
```

**Response:** List of papers with title, authors, abstract, URL, DOI, publication date, and PDF link.

#### PubMed Search
Search PubMed for biomedical and life sciences papers.

**API Endpoint:** `POST /research/pubmed`

**Request:**
```json
{
  "query": "CRISPR gene editing",
  "max_results": 10
}
```

**Response:** List of papers with full metadata.

### 2. Web Scraping

Extract content from academic webpages.

**API Endpoint:** `POST /research/scrape`

**Request:**
```json
{
  "url": "https://arxiv.org/abs/1706.03762",
  "selector": "div.abstract",
  "extract_links": false
}
```

**Response:** Scraped content with title, text, links, and metadata.

### 3. Citation Formatting

Format papers in multiple citation styles (BibTeX, APA, MLA, Chicago).

**API Endpoint:** `POST /research/cite`

**Request:**
```json
{
  "paper": {
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", "Noam Shazeer"],
    "url": "https://arxiv.org/abs/1706.03762",
    "published_date": "2017",
    "doi": "10.48550/arXiv.1706.03762",
    "journal": "NeurIPS 2017",
    "source": "arxiv"
  },
  "format": "bibtex"
}
```

**Response:** Formatted citation string.

### 4. Saved Citations

Save and manage citation collections.

**Endpoints:**
- `POST /research/citations` - Save a citation
- `GET /research/citations` - List all saved citations
- `GET /research/citations/{id}` - Get specific citation
- `DELETE /research/citations/{id}` - Delete citation

## Agent Tools

Research tools can be used by AI agents when `has_research_tools=True`:

### Available Tools

1. **search_arxiv_papers(query, max_results=10)**
   - Search ArXiv for papers
   - Returns list of paper dictionaries

2. **search_pubmed_papers(query, max_results=10)**
   - Search PubMed for biomedical papers
   - Returns list of paper dictionaries

3. **scrape_webpage_content(url, selector=None)**
   - Scrape content from a webpage
   - Returns dict with title, content, links, metadata

4. **format_paper_citation(title, authors, url, ...)**
   - Format a citation in specified style
   - Supports bibtex, apa, mla, chicago formats

## Example Usage

### Creating a Research Agent

```python
from agents import create_agent

agent = create_agent(
    system_prompt="You are a helpful research assistant. Help users find academic papers and generate citations.",
    model_id="openrouter/anthropic/claude-3.5-sonnet",
    temperature=0.7,
    has_research_tools=True
)
```

### Using Research Tools in Agent

```python
from agents import run_agent, AgentDependencies
import httpx

deps = AgentDependencies(
    http_client=httpx.AsyncClient(timeout=30.0)
)

result = await run_agent(
    agent,
    "Find me papers about quantum computing from ArXiv",
    deps=deps
)
```

## Database Schema

### SavedCitation Table

```python
class SavedCitation(Base):
    id: int                    # Primary key
    paper_data: dict           # JSON storage of paper metadata
    format: str                # Citation format preference
    notes: Optional[str]       # User notes
    created_at: datetime       # Timestamp
```

## Implementation Files

### Backend
- `backend/research_tools.py` - Core research functions (ArXiv, PubMed, scraping, citations)
- `backend/research_schemas.py` - Pydantic models for API
- `backend/models.py` - SavedCitation database model
- `backend/agents.py` - Research tool registration for agents
- `backend/main.py` - FastAPI endpoints

### Dependencies
- **httpx** - Async HTTP client
- **beautifulsoup4** - HTML parsing
- **lxml** - XML/HTML parser

## API Testing

### Test ArXiv Search
```bash
curl -X POST http://localhost:8000/research/arxiv \
  -H "Content-Type: application/json" \
  -d '{"query": "neural networks", "max_results": 5}'
```

### Test PubMed Search
```bash
curl -X POST http://localhost:8000/research/pubmed \
  -H "Content-Type: application/json" \
  -d '{"query": "COVID-19 vaccine", "max_results": 5}'
```

### Test Web Scraping
```bash
curl -X POST http://localhost:8000/research/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://arxiv.org/abs/1706.03762"}'
```

## Future Enhancements

Potential future additions:
- Google Scholar integration
- Semantic Scholar API
- Reference management (BibTeX file import/export)
- PDF text extraction
- Citation graph visualization
- Collaborative citation libraries
- Frontend Streamlit interface for research workflows

## Notes

- ArXiv and PubMed APIs are used directly via HTTP (no library wrappers due to dependency conflicts)
- Citation formatting is implemented manually without external libraries
- All search functions support async operations
- Rate limiting should be implemented for production use
- Consider caching frequently accessed papers

## License

MIT
