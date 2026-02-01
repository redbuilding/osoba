#!/usr/bin/env python3
"""
Polite Content Extraction with Structured Parsing
"""
import asyncio
import httpx
from dataclasses import dataclass
from typing import List, Dict
import re
from urllib.robotparser import RobotFileParser

@dataclass
class SmartExtractionConfig:
    max_urls: int = 3
    max_chars_per_url: int = 2000
    max_total_chars: int = 5000
    extract_headings: bool = True
    extract_paragraphs: bool = True
    respect_robots: bool = True
    request_delay: float = 1.0
    user_agent: str = "OhSee-AI-Assistant/1.0 (Polite Content Extraction)"

class PoliteContentExtractor:
    def __init__(self, config: SmartExtractionConfig):
        self.config = config
        self.total_chars_extracted = 0
    
    async def check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt"""
        if not self.config.respect_robots:
            return True
            
        try:
            base_url = f"{url.split('://')[0]}://{url.split('/')[2]}"
            robots_url = f"{base_url}/robots.txt"
            
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    rp = RobotFileParser()
                    rp.set_url(robots_url)
                    rp.read()
                    return rp.can_fetch(self.config.user_agent, url)
        except:
            pass  # If robots.txt check fails, assume allowed
        return True
    
    def extract_structured_content(self, html: str) -> Dict[str, str]:
        """Extract headings and paragraphs from HTML"""
        content = {"headings": [], "paragraphs": []}
        
        if self.config.extract_headings:
            # Extract h1, h2, h3 headings
            heading_pattern = r'<h[1-3][^>]*>(.*?)</h[1-3]>'
            headings = re.findall(heading_pattern, html, re.IGNORECASE | re.DOTALL)
            content["headings"] = [self.clean_text(h) for h in headings]
        
        if self.config.extract_paragraphs:
            # Extract paragraph content
            paragraph_pattern = r'<p[^>]*>(.*?)</p>'
            paragraphs = re.findall(paragraph_pattern, html, re.IGNORECASE | re.DOTALL)
            content["paragraphs"] = [self.clean_text(p) for p in paragraphs if len(self.clean_text(p)) > 50]
        
        return content
    
    def clean_text(self, text: str) -> str:
        """Clean HTML tags and normalize whitespace"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def format_extracted_content(self, content: Dict[str, str], max_chars: int) -> str:
        """Format extracted content with character limits"""
        formatted = []
        char_count = 0
        
        # Add headings first (they're usually more important)
        for heading in content["headings"]:
            if char_count + len(heading) + 10 > max_chars:  # +10 for formatting
                break
            formatted.append(f"## {heading}")
            char_count += len(heading) + 10
        
        # Add paragraphs
        for paragraph in content["paragraphs"]:
            if char_count + len(paragraph) + 2 > max_chars:  # +2 for newlines
                # Add truncated paragraph if there's space
                remaining_chars = max_chars - char_count - 5  # -5 for "..."
                if remaining_chars > 100:  # Only if meaningful content can fit
                    formatted.append(paragraph[:remaining_chars] + "...")
                break
            formatted.append(paragraph)
            char_count += len(paragraph) + 2
        
        return "\n\n".join(formatted)
    
    async def extract_from_url(self, url: str, title: str) -> Dict:
        """Extract content from a single URL with all safety checks"""
        
        # Check robots.txt
        if not await self.check_robots_txt(url):
            return {
                "url": url,
                "title": title,
                "status": "blocked",
                "reason": "Blocked by robots.txt",
                "content": ""
            }
        
        # Check if we've hit total character limit
        if self.total_chars_extracted >= self.config.max_total_chars:
            return {
                "url": url,
                "title": title,
                "status": "skipped",
                "reason": "Total character limit reached",
                "content": ""
            }
        
        try:
            # Polite delay
            await asyncio.sleep(self.config.request_delay)
            
            # Fetch content
            headers = {"User-Agent": self.config.user_agent}
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
            
            # Extract structured content
            structured_content = self.extract_structured_content(response.text)
            
            # Format with character limits
            remaining_total_chars = self.config.max_total_chars - self.total_chars_extracted
            max_chars_for_this_url = min(self.config.max_chars_per_url, remaining_total_chars)
            
            formatted_content = self.format_extracted_content(structured_content, max_chars_for_this_url)
            
            # Update total character count
            self.total_chars_extracted += len(formatted_content)
            
            return {
                "url": url,
                "title": title,
                "status": "success",
                "content": formatted_content,
                "content_length": len(formatted_content),
                "headings_found": len(structured_content["headings"]),
                "paragraphs_found": len(structured_content["paragraphs"])
            }
            
        except Exception as e:
            return {
                "url": url,
                "title": title,
                "status": "error",
                "reason": str(e),
                "content": ""
            }

async def demo_smart_extraction():
    """Demo the complete smart extraction workflow"""
    
    config = SmartExtractionConfig(
        max_urls=2,
        max_chars_per_url=1500,
        max_total_chars=3000,
        request_delay=0.5  # Faster for demo
    )
    
    extractor = PoliteContentExtractor(config)
    
    # Simulate prioritized URLs
    prioritized_urls = [
        {
            "url": "https://zapier.com/mcp",
            "title": "Connect AI tools to 8,000 apps with Zapier MCP",
            "priority_score": 31.0
        },
        {
            "url": "https://help.zapier.com/hc/en-us/articles/36265392843917-Use-Zapier-MCP-with-your-client",
            "title": "Use Zapier MCP with your client",
            "priority_score": 25.0
        }
    ]
    
    print("🤖 SMART CONTENT EXTRACTION DEMO")
    print("=" * 50)
    print(f"Config: max_urls={config.max_urls}, max_chars_per_url={config.max_chars_per_url}")
    print(f"Total limit: {config.max_total_chars} chars, delay: {config.request_delay}s")
    print()
    
    results = []
    for item in prioritized_urls[:config.max_urls]:
        print(f"📄 Extracting from: {item['title']}")
        result = await extractor.extract_from_url(item["url"], item["title"])
        results.append(result)
        
        print(f"   Status: {result['status']}")
        if result['status'] == 'success':
            print(f"   Content length: {result['content_length']} chars")
            print(f"   Headings: {result['headings_found']}, Paragraphs: {result['paragraphs_found']}")
        print()
    
    print(f"📊 Total characters extracted: {extractor.total_chars_extracted}")
    return results

if __name__ == "__main__":
    asyncio.run(demo_smart_extraction())
