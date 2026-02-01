# Web Content Extraction Best Practices in Python

## 1. HTTP Client Libraries

### httpx vs requests

**httpx** (Recommended for new projects):
- Async/await support built-in
- HTTP/2 support
- Better connection pooling
- Type hints throughout
- Drop-in replacement for requests API

```python
import httpx

# Sync usage
with httpx.Client() as client:
    response = client.get('https://example.com')

# Async usage
async with httpx.AsyncClient() as client:
    response = await client.get('https://example.com')
```

**requests** (Mature, widely adopted):
- Stable, battle-tested
- Extensive ecosystem
- Simpler for basic use cases
- No built-in async support

```python
import requests

response = requests.get('https://example.com')
```

**Documentation:**
- httpx: https://www.python-httpx.org/
- requests: https://requests.readthedocs.io/

## 2. HTML Parsing Libraries

### BeautifulSoup vs lxml

**BeautifulSoup** (Recommended for beginners):
- Forgiving parser, handles malformed HTML
- Intuitive API
- Multiple parser backends (html.parser, lxml, html5lib)

```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html_content, 'lxml')
title = soup.find('title').get_text()
```

**lxml** (Performance-focused):
- Fastest XML/HTML parser
- XPath support
- Lower-level API
- Stricter parsing

```python
from lxml import html

tree = html.fromstring(html_content)
title = tree.xpath('//title/text()')[0]
```

**Documentation:**
- BeautifulSoup: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- lxml: https://lxml.de/

## 3. Content Cleaning and Text Extraction

### Text Extraction Libraries

**trafilatura** (Recommended):
- Specialized for main content extraction
- Removes boilerplate (ads, navigation, etc.)
- Language detection
- Metadata extraction

```python
import trafilatura

url = 'https://example.com/article'
downloaded = trafilatura.fetch_url(url)
text = trafilatura.extract(downloaded)
```

**newspaper3k**:
- Article-focused extraction
- Author, publish date detection
- Image extraction

```python
from newspaper import Article

article = Article(url)
article.download()
article.parse()
text = article.text
```

**readability-lxml**:
- Port of Mozilla's Readability
- Good for article content

```python
from readability import Document

doc = Document(html_content)
clean_html = doc.summary()
```

### Manual Cleaning Approaches

```python
import re
from bs4 import BeautifulSoup

def clean_text(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text and clean whitespace
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text
```

**Documentation:**
- trafilatura: https://trafilatura.readthedocs.io/
- newspaper3k: https://newspaper.readthedocs.io/
- readability-lxml: https://github.com/buriy/python-readability

## 4. Rate Limiting and Polite Crawling

### Rate Limiting Libraries

**ratelimit**:
```python
from ratelimit import limits, sleep_and_retry
import requests

@sleep_and_retry
@limits(calls=1, period=1)  # 1 call per second
def fetch_url(url):
    return requests.get(url)
```

**aiohttp with asyncio.Semaphore**:
```python
import asyncio
import aiohttp

async def fetch_with_limit(session, url, semaphore):
    async with semaphore:
        async with session.get(url) as response:
            return await response.text()

# Limit to 5 concurrent requests
semaphore = asyncio.Semaphore(5)
```

### Polite Crawling Best Practices

**robots.txt Compliance**:
```python
import urllib.robotparser

def can_fetch(url, user_agent='*'):
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{url}/robots.txt")
    rp.read()
    return rp.can_fetch(user_agent, url)
```

**Respectful Headers**:
```python
headers = {
    'User-Agent': 'YourBot/1.0 (contact@example.com)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}
```

**Exponential Backoff**:
```python
import time
import random

def fetch_with_backoff(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response
        except requests.RequestException:
            pass
        
        if attempt < max_retries - 1:
            delay = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
    
    raise Exception(f"Failed to fetch {url} after {max_retries} attempts")
```

### Complete Example

```python
import httpx
import asyncio
from bs4 import BeautifulSoup
from ratelimit import limits, sleep_and_retry
import trafilatura

class WebExtractor:
    def __init__(self, rate_limit=1):
        self.client = httpx.AsyncClient(
            headers={'User-Agent': 'WebExtractor/1.0'},
            timeout=30.0
        )
        self.semaphore = asyncio.Semaphore(rate_limit)
    
    async def extract_content(self, url):
        async with self.semaphore:
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                
                # Use trafilatura for main content
                text = trafilatura.extract(response.text)
                if not text:
                    # Fallback to BeautifulSoup
                    soup = BeautifulSoup(response.text, 'lxml')
                    text = soup.get_text()
                
                return text.strip()
            except Exception as e:
                print(f"Error extracting {url}: {e}")
                return None
    
    async def close(self):
        await self.client.aclose()
```

**Documentation:**
- ratelimit: https://pypi.org/project/ratelimit/
- aiohttp: https://docs.aiohttp.org/
- urllib.robotparser: https://docs.python.org/3/library/urllib.robotparser.html

## Additional Resources

- **Scrapy Framework**: https://scrapy.org/ (for large-scale crawling)
- **Playwright**: https://playwright.dev/python/ (for JavaScript-heavy sites)
- **Selenium**: https://selenium-python.readthedocs.io/ (browser automation)
- **Web Scraping Ethics**: https://blog.apify.com/web-scraping-ethics/