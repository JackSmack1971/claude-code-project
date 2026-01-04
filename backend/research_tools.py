"""
Research assistant tools for academic search and web scraping.
Implements ArXiv search, PubMed search, web scraping, and citation formatting.
"""
import httpx
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
from research_schemas import (
    PaperResult,
    PaperSource,
    CitationFormat,
    ScrapeResult
)


# ArXiv API Documentation: https://info.arxiv.org/help/api/index.html
ARXIV_API_URL = "http://export.arxiv.org/api/query"
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


async def search_arxiv(
    query: str,
    max_results: int = 10,
    http_client: Optional[httpx.AsyncClient] = None
) -> List[PaperResult]:
    """
    Search ArXiv for academic papers.

    Args:
        query: Search query string (supports ArXiv query syntax)
        max_results: Maximum number of results to return (1-100)
        http_client: Optional async HTTP client

    Returns:
        List of PaperResult objects

    Raises:
        httpx.HTTPError: If API request fails

    Example:
        results = await search_arxiv("quantum computing", max_results=5)
    """
    close_client = False
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=30.0)
        close_client = True

    try:
        # Build ArXiv API query
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": min(max_results, 100),
            "sortBy": "relevance",
            "sortOrder": "descending"
        }

        response = await http_client.get(ARXIV_API_URL, params=params)
        response.raise_for_status()

        # Parse XML response
        root = ET.fromstring(response.text)
        ns = {"atom": "http://www.w3.org/2005/Atom",
              "arxiv": "http://arxiv.org/schemas/atom"}

        papers = []
        for entry in root.findall("atom:entry", ns):
            # Extract authors
            authors = []
            for author in entry.findall("atom:author/atom:name", ns):
                if author.text:
                    authors.append(author.text)

            # Extract published date
            published = entry.find("atom:published", ns)
            pub_date = published.text[:10] if published is not None and published.text else None

            # Extract DOI from links
            doi = None
            doi_link = entry.find("atom:link[@title='doi']", ns)
            if doi_link is not None and "href" in doi_link.attrib:
                doi = doi_link.attrib["href"].replace("http://dx.doi.org/", "")

            # Extract main URL and PDF URL
            main_url = entry.find("atom:id", ns)
            pdf_link = entry.find("atom:link[@title='pdf']", ns)

            # Extract title and abstract
            title_elem = entry.find("atom:title", ns)
            abstract_elem = entry.find("atom:summary", ns)

            if main_url is not None and main_url.text and title_elem is not None:
                paper = PaperResult(
                    title=title_elem.text.strip() if title_elem.text else "",
                    authors=authors,
                    abstract=abstract_elem.text.strip() if abstract_elem is not None and abstract_elem.text else None,
                    url=main_url.text.strip(),
                    doi=doi,
                    published_date=pub_date,
                    journal="arXiv",
                    source=PaperSource.ARXIV,
                    pdf_url=pdf_link.attrib.get("href") if pdf_link is not None else None
                )
                papers.append(paper)

        return papers

    finally:
        if close_client:
            await http_client.aclose()


async def search_pubmed(
    query: str,
    max_results: int = 10,
    http_client: Optional[httpx.AsyncClient] = None
) -> List[PaperResult]:
    """
    Search PubMed for biomedical papers using NCBI E-utilities API.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (1-100)
        http_client: Optional async HTTP client

    Returns:
        List of PaperResult objects

    Raises:
        httpx.HTTPError: If API request fails

    Example:
        results = await search_pubmed("CRISPR gene editing", max_results=5)
    """
    close_client = False
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=30.0)
        close_client = True

    try:
        # Step 1: Search for PMIDs
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": min(max_results, 100),
            "retmode": "json"
        }

        search_response = await http_client.get(PUBMED_SEARCH_URL, params=search_params)
        search_response.raise_for_status()
        search_data = search_response.json()

        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            return []

        # Step 2: Fetch details for PMIDs
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml"
        }

        fetch_response = await http_client.get(PUBMED_FETCH_URL, params=fetch_params)
        fetch_response.raise_for_status()

        # Parse XML response
        root = ET.fromstring(fetch_response.text)
        papers = []

        for article in root.findall(".//PubmedArticle"):
            # Extract title
            title_elem = article.find(".//ArticleTitle")
            if title_elem is None or not title_elem.text:
                continue

            # Extract authors
            authors = []
            for author in article.findall(".//Author"):
                lastname = author.find("LastName")
                forename = author.find("ForeName")
                if lastname is not None and lastname.text:
                    name = lastname.text
                    if forename is not None and forename.text:
                        name = f"{forename.text} {name}"
                    authors.append(name)

            # Extract abstract
            abstract_elem = article.find(".//Abstract/AbstractText")
            abstract = abstract_elem.text if abstract_elem is not None and abstract_elem.text else None

            # Extract publication date
            pub_date = None
            pub_date_elem = article.find(".//PubDate")
            if pub_date_elem is not None:
                year = pub_date_elem.find("Year")
                month = pub_date_elem.find("Month")
                day = pub_date_elem.find("Day")
                if year is not None and year.text:
                    pub_date = year.text
                    if month is not None and month.text:
                        try:
                            month_num = datetime.strptime(month.text[:3], "%b").month
                            pub_date = f"{year.text}-{month_num:02d}"
                            if day is not None and day.text:
                                pub_date = f"{pub_date}-{day.text.zfill(2)}"
                        except ValueError:
                            pass

            # Extract PMID and DOI
            pmid_elem = article.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else None

            doi = None
            for article_id in article.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi" and article_id.text:
                    doi = article_id.text
                    break

            # Extract journal
            journal_elem = article.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None and journal_elem.text else "PubMed"

            # Build PubMed URL
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

            paper = PaperResult(
                title=title_elem.text.strip(),
                authors=authors,
                abstract=abstract,
                url=url,
                doi=doi,
                published_date=pub_date,
                journal=journal,
                source=PaperSource.PUBMED,
                pdf_url=None  # PubMed doesn't provide direct PDF links
            )
            papers.append(paper)

        return papers

    finally:
        if close_client:
            await http_client.aclose()


async def scrape_webpage(
    url: str,
    selector: Optional[str] = None,
    extract_links: bool = False,
    http_client: Optional[httpx.AsyncClient] = None
) -> ScrapeResult:
    """
    Scrape content from a webpage using BeautifulSoup.

    Args:
        url: URL to scrape
        selector: Optional CSS selector to extract specific content
        extract_links: Whether to extract all links from the page
        http_client: Optional async HTTP client

    Returns:
        ScrapeResult with extracted content

    Raises:
        httpx.HTTPError: If request fails

    Example:
        result = await scrape_webpage("https://example.com", selector="div.content")
    """
    close_client = False
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        close_client = True

    try:
        response = await http_client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Extract content
        if selector:
            selected = soup.select(selector)
            content = "\n".join([elem.get_text(strip=True) for elem in selected])
        else:
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            content = soup.get_text(separator="\n", strip=True)

        # Extract links if requested
        links = []
        if extract_links:
            for link in soup.find_all("a", href=True):
                link_text = link.get_text(strip=True)
                link_href = link["href"]
                if link_href:
                    links.append({"text": link_text, "href": link_href})

        # Extract metadata
        metadata = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content_val = meta.get("content")
            if name and content_val:
                metadata[name] = content_val

        return ScrapeResult(
            url=url,
            title=title,
            content=content,
            links=links,
            metadata=metadata
        )

    finally:
        if close_client:
            await http_client.aclose()


def format_citation(paper: PaperResult, format: CitationFormat) -> str:
    """
    Format a paper citation in the specified format.

    Args:
        paper: PaperResult to format
        format: Desired citation format (BibTeX, APA, MLA, Chicago)

    Returns:
        Formatted citation string

    Example:
        citation = format_citation(paper, CitationFormat.BIBTEX)
    """
    if format == CitationFormat.BIBTEX:
        return _format_bibtex(paper)
    elif format == CitationFormat.APA:
        return _format_apa(paper)
    elif format == CitationFormat.MLA:
        return _format_mla(paper)
    elif format == CitationFormat.CHICAGO:
        return _format_chicago(paper)
    else:
        raise ValueError(f"Unsupported citation format: {format}")


def _format_bibtex(paper: PaperResult) -> str:
    """Format paper as BibTeX entry."""
    # Generate cite key from first author and year
    year = paper.published_date[:4] if paper.published_date else "n.d."
    first_author = paper.authors[0].split()[-1].lower() if paper.authors else "unknown"
    cite_key = f"{first_author}{year}"

    # Format authors for BibTeX
    authors_str = " and ".join(paper.authors) if paper.authors else "Unknown"

    entry_type = "article"
    bibtex = f"@{entry_type}{{{cite_key},\n"
    bibtex += f"  title={{{paper.title}}},\n"
    bibtex += f"  author={{{authors_str}}},\n"

    if paper.journal:
        bibtex += f"  journal={{{paper.journal}}},\n"

    if paper.published_date:
        bibtex += f"  year={{{year}}},\n"

    if paper.doi:
        bibtex += f"  doi={{{paper.doi}}},\n"

    if paper.url:
        bibtex += f"  url={{{paper.url}}},\n"

    bibtex += "}"
    return bibtex


def _format_apa(paper: PaperResult) -> str:
    """Format paper in APA style (7th edition)."""
    year = paper.published_date[:4] if paper.published_date else "n.d."

    # Format authors (Last, F. M.)
    author_parts = []
    for author in paper.authors[:20]:  # APA uses et al. after 20
        name_parts = author.split()
        if len(name_parts) >= 2:
            last = name_parts[-1]
            initials = ". ".join([n[0] for n in name_parts[:-1]]) + "."
            author_parts.append(f"{last}, {initials}")
        else:
            author_parts.append(author)

    if len(paper.authors) > 20:
        authors_str = ", ".join(author_parts[:19]) + ", ... " + author_parts[-1]
    elif len(author_parts) > 1:
        authors_str = ", ".join(author_parts[:-1]) + ", & " + author_parts[-1]
    elif author_parts:
        authors_str = author_parts[0]
    else:
        authors_str = "Unknown"

    citation = f"{authors_str} ({year}). {paper.title}. "

    if paper.journal:
        citation += f"{paper.journal}. "

    if paper.doi:
        citation += f"https://doi.org/{paper.doi}"
    elif paper.url:
        citation += paper.url

    return citation


def _format_mla(paper: PaperResult) -> str:
    """Format paper in MLA style (9th edition)."""
    # Format authors (Last, First)
    if paper.authors:
        first_author = paper.authors[0]
        name_parts = first_author.split()
        if len(name_parts) >= 2:
            authors_str = f"{name_parts[-1]}, {' '.join(name_parts[:-1])}"
        else:
            authors_str = first_author

        if len(paper.authors) > 1:
            authors_str += ", et al."
    else:
        authors_str = "Unknown"

    citation = f"{authors_str}. \"{paper.title}.\" "

    if paper.journal:
        citation += f"{paper.journal}, "

    if paper.published_date:
        year = paper.published_date[:4]
        citation += f"{year}, "

    citation += paper.url + "."

    return citation


def _format_chicago(paper: PaperResult) -> str:
    """Format paper in Chicago style (author-date)."""
    year = paper.published_date[:4] if paper.published_date else "n.d."

    # Format authors (Last, First)
    if paper.authors:
        first_author = paper.authors[0]
        name_parts = first_author.split()
        if len(name_parts) >= 2:
            authors_str = f"{name_parts[-1]}, {' '.join(name_parts[:-1])}"
        else:
            authors_str = first_author

        if len(paper.authors) > 1:
            authors_str += " et al."
    else:
        authors_str = "Unknown"

    citation = f"{authors_str}. {year}. \"{paper.title}.\" "

    if paper.journal:
        citation += f"{paper.journal}. "

    if paper.doi:
        citation += f"https://doi.org/{paper.doi}."
    elif paper.url:
        citation += paper.url + "."

    return citation
