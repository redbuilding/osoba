# mcp_web_search_server.py
import os
import json
from dotenv import load_dotenv, find_dotenv
import httpx
from fastmcp import FastMCP
import logging
import sys
import time
import re
import asyncio
from urllib.robotparser import RobotFileParser
from dataclasses import dataclass
from typing import List, Dict
from utils.web_fetcher import WebFetcher
from utils.content_extractor import ContentExtractor

# Get a logger for this module specifically for setup and script-level messages
script_logger = logging.getLogger("server_search_script")
script_logger.setLevel(logging.INFO) # Set to DEBUG to see more detailed logs from here
if not script_logger.hasHandlers():
    stderr_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [SERVER_SEARCH] %(message)s')
    stderr_handler.setFormatter(formatter)
    script_logger.addHandler(stderr_handler)
    script_logger.propagate = False

script_logger.info(f"Script starting. Python Executable: {sys.executable}")
script_logger.info(f"Current Working Directory (CWD): {os.getcwd()}")

# Load environment variables from .env file
dotenv_path = find_dotenv(usecwd=False, raise_error_if_not_found=False)
if dotenv_path:
    script_logger.info(f"Loading .env file from: {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    script_logger.warning("No .env file found by find_dotenv(). Relying on default load_dotenv() or existing environment variables.")
    load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
if SERPER_API_KEY and len(SERPER_API_KEY) > 5:
    script_logger.info(f"SERPER_API_KEY found (length: {len(SERPER_API_KEY)}).")
else:
    script_logger.critical(f"SERPER_API_KEY environment variable NOT FOUND or is too short.")
    raise ValueError("SERPER_API_KEY environment variable not set or invalid. Please ensure it's in your .env file or environment.")

SERPER_API_URL = "https://google.serper.dev/search"
script_logger.info("Environment variables processed. SERPER_API_URL configured.")

@dataclass
class SmartExtractionConfig:
    max_urls: int = int(os.getenv("SMART_EXTRACT_MAX_URLS", "3"))
    max_chars_per_url: int = int(os.getenv("SMART_EXTRACT_MAX_CHARS_PER_URL", "2000"))
    max_total_chars: int = int(os.getenv("SMART_EXTRACT_MAX_TOTAL_CHARS", "5000"))
    request_delay: float = float(os.getenv("SMART_EXTRACT_REQUEST_DELAY", "1.0"))
    user_agent: str = "Osoba-AI-Assistant/1.0 (Polite Content Extraction)"

# Create an MCP server instance using FastMCP
# Note: Remove the explicit transport configuration - FastMCP handles this
mcp = FastMCP(
    name="WebSearchServer",
    version="0.1.0",
    instructions="Provides web search functionality via the Serper.dev API.",
)
script_logger.info("FastMCP instance created.")

# Register an asynchronous tool for performing web searches
@mcp.tool()
async def web_search(query: str, num_results: int = 10, location: str = "us", language: str = "en") -> dict:
    """
    Performs a web search using the Serper.dev API and returns comprehensive results.

    Args:
        query: The search query string
        num_results: Number of results to return (default: 10, max: 100)
        location: Search location/country code (default: "us")
        language: Search language code (default: "en")

    Returns:
        A comprehensive dictionary containing all available search result types
    """
    if not query:
        script_logger.warning("web_search called with empty query.")
        return {
            "status": "error",
            "message": "Missing required parameter 'query' for web_search tool.",
            "results": [] # Consistent with error structure
        }

    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Enhanced payload with additional parameters
    payload = json.dumps({
        "q": query,
        "num": min(num_results, 100),  # Cap at 100 per Serper limits
        "gl": location,  # Geographic location
        "hl": language   # Language
    })

    try:
        script_logger.info(f"Performing search for: '{query}'")
        start_time = time.time()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(SERPER_API_URL, headers=headers, data=payload)
        end_time = time.time()
        script_logger.info(f"Serper API call took {end_time - start_time:.2f} seconds")
        response.raise_for_status()
        search_results = response.json() # This is already a dict
        script_logger.info(f"Search successful for: '{query}'")

        # Log the actual results for debugging
        # Use INFO level for this potentially large log, or DEBUG if preferred for less noise
        script_logger.debug(f"Serper API response: {json.dumps(search_results, indent=2)}")

        # Return a single dict (not a list!)
        result = {
            "status": "success",
            "message": f"Search completed for: {query}",
            "query": query,
            "organic_results": search_results.get("organic", []),
            "top_stories": search_results.get("topStories", []),
            "people_also_ask": search_results.get("peopleAlsoAsk", []),
            "knowledge_graph": search_results.get("knowledgeGraph", {}),
            "answer_box": search_results.get("answerBox", {}),
            "related_searches": search_results.get("relatedSearches", []),
            "shopping_results": search_results.get("shopping", []),
            "images": search_results.get("images", [])
        }

        script_logger.debug(f"Returning result: {json.dumps(result, indent=2)}")
        return result # Ensure this is a dict

    except httpx.TimeoutException:
        script_logger.error(f"Timeout calling Serper.dev API for query '{query}'")
        return {"status": "error", "message": f"Timeout performing search for: {query}", "results": []}
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        try:
            error_detail = e.response.json()
        except json.JSONDecodeError:
            pass
        script_logger.error(f"HTTP error for query '{query}': {e.response.status_code}. Response: {error_detail}")
        return {"status": "error", "message": f"API Error ({e.response.status_code}): {error_detail}", "results": []}
    except Exception as e:
        script_logger.exception(f"Unexpected error during web_search for query '{query}': {e}")
        return {"status": "error", "message": str(e), "results": []}

script_logger.info("web_search tool defined.")

# Register specialized search tools for different content types
@mcp.tool()
async def image_search(query: str, num_results: int = 10) -> dict:
    """
    Performs an image search using the Serper.dev API.

    Args:
        query: The search query string
        num_results: Number of image results to return (default: 10)

    Returns:
        Dictionary containing image search results
    """
    if not query:
        return {"status": "error", "message": "Missing required parameter 'query'"}

    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    payload = json.dumps({"q": query, "num": min(num_results, 100)})

    try:
        script_logger.info(f"Performing image search for: '{query}'")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://google.serper.dev/images", headers=headers, data=payload)
        response.raise_for_status()
        results = response.json()
        
        return {
            "status": "success",
            "message": f"Image search completed for: {query}",
            "query": query,
            "images": results.get("images", [])
        }
    except Exception as e:
        script_logger.error(f"Image search error for '{query}': {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def news_search(query: str, num_results: int = 10) -> dict:
    """
    Performs a news search using the Serper.dev API.

    Args:
        query: The search query string
        num_results: Number of news results to return (default: 10)

    Returns:
        Dictionary containing news search results
    """
    if not query:
        return {"status": "error", "message": "Missing required parameter 'query'"}

    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    payload = json.dumps({"q": query, "num": min(num_results, 100)})

    try:
        script_logger.info(f"Performing news search for: '{query}'")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://google.serper.dev/news", headers=headers, data=payload)
        response.raise_for_status()
        results = response.json()
        
        return {
            "status": "success",
            "message": f"News search completed for: {query}",
            "query": query,
            "news": results.get("news", [])
        }
    except Exception as e:
        script_logger.error(f"News search error for '{query}': {e}")
        return {"status": "error", "message": str(e)}

script_logger.info("Enhanced search and extraction tools defined.")

def calculate_url_priority(search_result: dict, query_terms: List[str]) -> List[dict]:
    """Calculate priority score for each discovered URL"""
    priorities = []
    
    for result in search_result.get("organic_results", []):
        score = 0
        
        # Base score from search position
        position_score = max(0, 10 - result.get("position", 10))
        score += position_score
        
        # Title relevance
        title = result.get("title", "").lower()
        title_matches = sum(1 for term in query_terms if term.lower() in title)
        score += title_matches * 3
        
        # Snippet relevance
        snippet = result.get("snippet", "").lower()
        snippet_matches = sum(1 for term in query_terms if term.lower() in snippet)
        score += snippet_matches * 2
        
        # Sitelinks bonus
        sitelinks_count = len(result.get("sitelinks", []))
        score += min(sitelinks_count, 3) * 1.5
        
        # Domain authority heuristics
        url = result.get("link", "")
        if any(domain in url for domain in ["docs.", "help.", "guide.", "tutorial."]):
            score += 2
        
        priorities.append({
            "url": url,
            "title": result.get("title", ""),
            "snippet": result.get("snippet", ""),
            "priority_score": score
        })
    
    return sorted(priorities, key=lambda x: x["priority_score"], reverse=True)

class PoliteContentExtractor:
    def __init__(self, config: SmartExtractionConfig):
        self.config = config
        self.total_chars_extracted = 0
    
    def clean_text(self, text: str) -> str:
        """Clean HTML tags and normalize whitespace"""
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        return re.sub(r'\s+', ' ', text).strip()
    
    def extract_structured_content(self, html: str) -> Dict[str, List[str]]:
        """Extract headings and paragraphs from HTML"""
        content = {"headings": [], "paragraphs": []}
        
        # Extract headings
        heading_pattern = r'<h[1-3][^>]*>(.*?)</h[1-3]>'
        headings = re.findall(heading_pattern, html, re.IGNORECASE | re.DOTALL)
        content["headings"] = [self.clean_text(h) for h in headings if len(self.clean_text(h)) > 5]
        
        # Extract paragraphs
        paragraph_pattern = r'<p[^>]*>(.*?)</p>'
        paragraphs = re.findall(paragraph_pattern, html, re.IGNORECASE | re.DOTALL)
        content["paragraphs"] = [self.clean_text(p) for p in paragraphs if len(self.clean_text(p)) > 50]
        
        return content
    
    def format_content(self, content: Dict[str, List[str]], max_chars: int) -> str:
        """Format extracted content with character limits"""
        formatted = []
        char_count = 0
        
        # Add headings first
        for heading in content["headings"][:5]:  # Limit headings
            if char_count + len(heading) + 10 > max_chars:
                break
            formatted.append(f"## {heading}")
            char_count += len(heading) + 10
        
        # Add paragraphs
        for paragraph in content["paragraphs"][:10]:  # Limit paragraphs
            if char_count + len(paragraph) + 2 > max_chars:
                remaining = max_chars - char_count - 5
                if remaining > 100:
                    formatted.append(paragraph[:remaining] + "...")
                break
            formatted.append(paragraph)
            char_count += len(paragraph) + 2
        
        return "\n\n".join(formatted)
    
    async def extract_from_url(self, url: str, title: str) -> Dict:
        """Extract content from a single URL using enhanced utilities"""
        if self.total_chars_extracted >= self.config.max_total_chars:
            return {"url": url, "title": title, "status": "skipped", "content": ""}
        
        try:
            # Use WebFetcher for robust HTTP handling
            web_fetcher = WebFetcher(
                user_agent=self.config.user_agent,
                request_delay=self.config.request_delay,
                timeout=10
            )
            
            fetch_result = await web_fetcher.fetch_content(url)
            if fetch_result["status"] != "success":
                return {
                    "url": url,
                    "title": title,
                    "status": "error",
                    "content": "",
                    "error": fetch_result.get("message", "Failed to fetch content")
                }
            
            # Use ContentExtractor for robust content extraction
            remaining_chars = min(
                self.config.max_chars_per_url,
                self.config.max_total_chars - self.total_chars_extracted
            )
            
            content_extractor = ContentExtractor(max_chars=remaining_chars)
            extraction_result = content_extractor.extract_content(fetch_result["content"], url)
            
            if extraction_result["status"] != "success":
                return {
                    "url": url,
                    "title": title,
                    "status": "error",
                    "content": "",
                    "error": extraction_result.get("message", "Failed to extract content")
                }
            
            extracted_content = extraction_result["content"]
            self.total_chars_extracted += len(extracted_content)
            
            return {
                "url": url,
                "title": title,
                "status": "success",
                "content": extracted_content,
                "content_length": len(extracted_content),
                "extraction_method": extraction_result.get("method", "unknown"),
                "fetch_time": fetch_result.get("fetch_time", 0)
            }
            
        except Exception as e:
            script_logger.error(f"Content extraction failed for {url}: {e}")
            return {"url": url, "title": title, "status": "error", "content": "", "error": str(e)}

@mcp.tool()
async def smart_search_extract(
    query: str, 
    max_urls: int = 3, 
    max_chars_per_url: int = 2000, 
    max_total_chars: int = 5000
) -> dict:
    """
    Intelligent search with prioritized content extraction from top results.
    
    Args:
        query: Search query string
        max_urls: Maximum URLs to extract content from (default: 3)
        max_chars_per_url: Character limit per webpage (default: 2000)
        max_total_chars: Total character limit across all URLs (default: 5000)
    
    Returns:
        Dictionary with search results, prioritized URLs, and extracted content
    """
    if not query:
        return {"status": "error", "message": "Missing required parameter 'query'"}
    
    try:
        # Step 1: Perform search
        search_result = await web_search(query, num_results=10)
        if search_result["status"] != "success":
            return search_result
        
        # Step 2: Prioritize URLs
        query_terms = query.split()
        prioritized_urls = calculate_url_priority(search_result, query_terms)
        
        # Step 3: Extract content from top URLs
        config = SmartExtractionConfig(
            max_urls=max_urls,
            max_chars_per_url=max_chars_per_url,
            max_total_chars=max_total_chars
        )
        extractor = PoliteContentExtractor(config)
        
        extracted_content = []
        for url_info in prioritized_urls[:max_urls]:
            content = await extractor.extract_from_url(url_info["url"], url_info["title"])
            extracted_content.append(content)
        
        return {
            "status": "success",
            "message": f"Smart extraction completed for: {query}",
            "query": query,
            "search_summary": {
                "total_results": len(search_result.get("organic_results", [])),
                "related_searches": search_result.get("related_searches", [])
            },
            "prioritized_urls": prioritized_urls[:max_urls],
            "extracted_content": extracted_content,
            "extraction_stats": {
                "urls_processed": len(extracted_content),
                "successful_extractions": len([c for c in extracted_content if c["status"] == "success"]),
                "total_chars_extracted": extractor.total_chars_extracted
            }
        }
        
    except Exception as e:
        script_logger.error(f"Smart extraction error for '{query}': {e}")
        return {"status": "error", "message": str(e)}

script_logger.info("Smart search and extraction tools defined.")

@mcp.tool()
async def fetch_url(url: str, max_chars: int = 5000) -> dict:
    """
    Fetch and extract readable content from a specific URL.

    Args:
        url: The URL to fetch content from
        max_chars: Maximum characters to return (default: 5000)

    Returns:
        Dictionary with extracted content and metadata
    """
    if not url:
        return {"status": "error", "message": "Missing required parameter 'url'"}

    try:
        web_fetcher = WebFetcher(
            user_agent="Osoba-AI-Assistant/1.0 (Polite Content Extraction)",
            request_delay=1.0,
            timeout=10
        )
        fetch_result = await web_fetcher.fetch_content(url)
        if fetch_result["status"] != "success":
            return {
                "status": "error",
                "message": fetch_result.get("message", "Failed to fetch URL"),
                "url": url
            }

        content_extractor = ContentExtractor(max_chars=max_chars)
        extraction_result = content_extractor.extract_content(fetch_result["content"], url)
        if extraction_result["status"] != "success":
            return {
                "status": "error",
                "message": extraction_result.get("message", "Failed to extract content"),
                "url": url
            }

        return {
            "status": "success",
            "url": fetch_result.get("url", url),
            "content": extraction_result["content"],
            "title": extraction_result.get("title", ""),
            "content_length": extraction_result.get("content_length", 0),
            "extraction_method": extraction_result.get("method", "unknown"),
            "fetch_time": fetch_result.get("fetch_time", 0)
        }

    except Exception as e:
        script_logger.error(f"fetch_url error for '{url}': {e}")
        return {"status": "error", "message": str(e), "url": url}

script_logger.info("fetch_url tool defined.")

# For FastMCP, we don't need a main block - the fastmcp CLI handles server startup
# But keep this for direct execution if needed
if __name__ == "__main__":
    script_logger.info("Note: This FastMCP server should be run using 'fastmcp dev server_search.py' for development.")
    script_logger.info("If you need to run it directly, consider using the standard MCP server pattern instead.")
