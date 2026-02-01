import re
import logging
from typing import Dict, List, Optional
try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False
    
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

logger = logging.getLogger("content_extractor")

class ContentExtractor:
    """Enhanced content extraction using trafilatura and BeautifulSoup."""
    
    def __init__(self, max_chars: int = 2000):
        self.max_chars = max_chars
        
        if not HAS_TRAFILATURA and not HAS_BS4:
            logger.warning("Neither trafilatura nor BeautifulSoup available. Content extraction will be limited.")
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
            
        # Remove HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove excessive newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text
    
    def extract_with_trafilatura(self, html: str, url: str = "") -> Optional[Dict]:
        """Extract content using trafilatura (primary method)"""
        if not HAS_TRAFILATURA:
            return None
            
        try:
            # Extract main content
            content = trafilatura.extract(html, url=url, include_comments=False, 
                                        include_tables=True, include_links=False)
            
            if not content:
                return None
            
            # Extract metadata
            metadata = trafilatura.extract_metadata(html)
            
            # Clean and truncate content
            clean_content = self.clean_text(content)
            if len(clean_content) > self.max_chars:
                clean_content = clean_content[:self.max_chars] + "..."
            
            return {
                "method": "trafilatura",
                "content": clean_content,
                "title": metadata.title if metadata else "",
                "author": metadata.author if metadata else "",
                "date": metadata.date if metadata else "",
                "description": metadata.description if metadata else "",
                "content_length": len(clean_content)
            }
            
        except Exception as e:
            logger.error(f"Trafilatura extraction failed: {e}")
            return None
    
    def extract_with_beautifulsoup(self, html: str) -> Optional[Dict]:
        """Extract content using BeautifulSoup (fallback method)"""
        if not HAS_BS4:
            return None
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # Extract title
            title_tag = soup.find('title')
            title = title_tag.get_text().strip() if title_tag else ""
            
            # Extract main content areas
            content_selectors = [
                'main', 'article', '[role="main"]', '.content', '.post-content',
                '.entry-content', '.article-content', '#content', '.main-content'
            ]
            
            main_content = None
            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            # If no main content area found, use body
            if not main_content:
                main_content = soup.find('body') or soup
            
            # Extract headings and paragraphs
            headings = []
            for h in main_content.find_all(['h1', 'h2', 'h3']):
                heading_text = self.clean_text(h.get_text())
                if len(heading_text) > 5:
                    headings.append(heading_text)
            
            paragraphs = []
            for p in main_content.find_all(['p', 'div']):
                para_text = self.clean_text(p.get_text())
                if len(para_text) > 20:  # Filter out very short paragraphs
                    paragraphs.append(para_text)
            
            # Combine content
            content_parts = []
            if headings:
                content_parts.extend([f"## {h}" for h in headings[:5]])
            if paragraphs:
                content_parts.extend(paragraphs[:10])
            
            combined_content = "\n\n".join(content_parts)
            clean_content = self.clean_text(combined_content)
            
            if len(clean_content) > self.max_chars:
                clean_content = clean_content[:self.max_chars] + "..."
            
            return {
                "method": "beautifulsoup",
                "content": clean_content,
                "title": self.clean_text(title),
                "headings_found": len(headings),
                "paragraphs_found": len(paragraphs),
                "content_length": len(clean_content)
            }
            
        except Exception as e:
            logger.error(f"BeautifulSoup extraction failed: {e}")
            return None
    
    def extract_content(self, html: str, url: str = "") -> Dict:
        """
        Extract clean content from HTML using best available method.
        
        Args:
            html: HTML content to extract from
            url: Original URL for context (optional)
            
        Returns:
            Dictionary with extracted content and metadata
        """
        if not html or not html.strip():
            return {
                "status": "error",
                "message": "Empty HTML content",
                "content": ""
            }
        
        # Try trafilatura first (best quality)
        result = self.extract_with_trafilatura(html, url)
        if result and result.get("content"):
            return {
                "status": "success",
                "message": f"Content extracted using {result['method']}",
                **result
            }
        
        # Fallback to BeautifulSoup
        result = self.extract_with_beautifulsoup(html)
        if result and result.get("content"):
            return {
                "status": "success", 
                "message": f"Content extracted using {result['method']}",
                **result
            }
        
        # Last resort: basic text extraction
        try:
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html)
            clean_content = self.clean_text(text)
            
            if len(clean_content) > self.max_chars:
                clean_content = clean_content[:self.max_chars] + "..."
            
            if clean_content:
                return {
                    "status": "success",
                    "message": "Content extracted using basic text extraction",
                    "method": "basic",
                    "content": clean_content,
                    "content_length": len(clean_content)
                }
        except Exception as e:
            logger.error(f"Basic text extraction failed: {e}")
        
        return {
            "status": "error",
            "message": "Failed to extract content with all methods",
            "content": ""
        }
