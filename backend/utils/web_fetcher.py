import asyncio
import time
import logging
from typing import Dict, Optional
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
import httpx

logger = logging.getLogger("web_fetcher")

class WebFetcher:
    """Async HTTP client wrapper with rate limiting and robots.txt compliance."""
    
    def __init__(self, user_agent: str = "OhSee-AI-Assistant/1.0 (Polite Content Extraction)", 
                 request_delay: float = 1.0, timeout: int = 10):
        self.user_agent = user_agent
        self.request_delay = request_delay
        self.timeout = timeout
        self.last_request_time = 0
        self._robots_cache: Dict[str, Optional[RobotFileParser]] = {}
    
    async def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt"""
        try:
            parsed_url = urlparse(url)
            domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if domain not in self._robots_cache:
                robots_url = urljoin(domain, "/robots.txt")
                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        response = await client.get(robots_url, headers={"User-Agent": self.user_agent})
                        if response.status_code == 200:
                            rp = RobotFileParser()
                            rp.set_url(robots_url)
                            rp.read()
                            # Parse the robots.txt content
                            for line in response.text.split('\n'):
                                rp.feed(line)
                            self._robots_cache[domain] = rp
                        else:
                            self._robots_cache[domain] = None
                except Exception:
                    self._robots_cache[domain] = None
            
            rp = self._robots_cache[domain]
            if rp:
                return rp.can_fetch(self.user_agent, url)
            return True  # If no robots.txt, assume allowed
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            return True  # Default to allowed on error
    
    async def _rate_limit(self):
        """Implement polite rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)
        self.last_request_time = time.time()
    
    async def fetch_content(self, url: str) -> Dict:
        """
        Fetch content from URL with rate limiting and robots.txt compliance.
        
        Args:
            url: URL to fetch content from
            
        Returns:
            Dictionary with status, content, and metadata
        """
        try:
            # Check robots.txt compliance
            if not await self._check_robots_txt(url):
                return {
                    "status": "error",
                    "message": "URL blocked by robots.txt",
                    "url": url
                }
            
            # Apply rate limiting
            await self._rate_limit()
            
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            start_time = time.time()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
            
            duration = time.time() - start_time
            logger.info(f"Fetched {url} in {duration:.2f}s (status: {response.status_code})")
            
            return {
                "status": "success",
                "content": response.text,
                "url": str(response.url),  # Final URL after redirects
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "content_length": len(response.text),
                "fetch_time": duration
            }
            
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching {url}")
            return {"status": "error", "message": "Request timeout", "url": url}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}")
            return {"status": "error", "message": f"HTTP {e.response.status_code}", "url": url}
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return {"status": "error", "message": str(e), "url": url}
