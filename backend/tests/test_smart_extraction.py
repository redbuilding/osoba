import pytest
import asyncio
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from server_search import smart_search_extract, calculate_url_priority, PoliteContentExtractor, SmartExtractionConfig
from utils.web_fetcher import WebFetcher
from utils.content_extractor import ContentExtractor

class TestSmartExtraction:
    """Test suite for smart extraction functionality"""
    
    @pytest.fixture
    def mock_search_results(self):
        """Mock search results for testing"""
        return {
            "status": "success",
            "organic_results": [
                {
                    "title": "Python Web Scraping Tutorial",
                    "snippet": "Learn how to scrape websites with Python using requests and BeautifulSoup",
                    "link": "https://example.com/python-scraping",
                    "position": 1
                },
                {
                    "title": "Advanced Web Scraping Techniques",
                    "snippet": "Advanced techniques for web scraping including handling JavaScript",
                    "link": "https://example.com/advanced-scraping",
                    "position": 2
                }
            ]
        }
    
    @pytest.fixture
    def mock_html_content(self):
        """Mock HTML content for testing"""
        return """
        <html>
        <head><title>Python Web Scraping Tutorial</title></head>
        <body>
            <h1>Introduction to Web Scraping</h1>
            <p>Web scraping is the process of extracting data from websites.</p>
            <h2>Getting Started</h2>
            <p>To get started with web scraping in Python, you'll need to install the requests and BeautifulSoup libraries.</p>
            <p>Here's a simple example of how to scrape a webpage.</p>
        </body>
        </html>
        """
    
    def test_calculate_url_priority(self, mock_search_results):
        """Test URL prioritization algorithm"""
        query_terms = ["python", "web", "scraping"]
        priorities = calculate_url_priority(mock_search_results, query_terms)
        
        assert len(priorities) == 2
        assert priorities[0]["priority_score"] > priorities[1]["priority_score"]
        assert "python-scraping" in priorities[0]["url"]
    
    @pytest.mark.asyncio
    async def test_web_fetcher_success(self, mock_html_content):
        """Test WebFetcher successful content retrieval"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.text = mock_html_content
            mock_response.status_code = 200
            mock_response.url = "https://example.com/test"
            mock_response.headers = {"content-type": "text/html"}
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            fetcher = WebFetcher()
            result = await fetcher.fetch_content("https://example.com/test")
            
            assert result["status"] == "success"
            assert result["content"] == mock_html_content
            assert result["status_code"] == 200
    
    @pytest.mark.asyncio
    async def test_web_fetcher_timeout(self):
        """Test WebFetcher timeout handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Request timeout")
            )
            
            fetcher = WebFetcher()
            result = await fetcher.fetch_content("https://example.com/test")
            
            assert result["status"] == "error"
            assert "timeout" in result["message"].lower()
    
    def test_content_extractor_with_trafilatura(self, mock_html_content):
        """Test ContentExtractor with trafilatura"""
        extractor = ContentExtractor(max_chars=1000)
        
        with patch('utils.content_extractor.HAS_TRAFILATURA', True):
            with patch('trafilatura.extract') as mock_extract:
                with patch('trafilatura.extract_metadata') as mock_metadata:
                    mock_extract.return_value = "This is extracted content from the webpage."
                    mock_metadata.return_value = MagicMock(
                        title="Test Title",
                        author="Test Author",
                        date="2024-01-01",
                        description="Test Description"
                    )
                    
                    result = extractor.extract_content(mock_html_content, "https://example.com/test")
                    
                    assert result["status"] == "success"
                    assert "trafilatura" in result["method"]
                    assert len(result["content"]) > 0
    
    def test_content_extractor_with_beautifulsoup(self, mock_html_content):
        """Test ContentExtractor with BeautifulSoup fallback"""
        extractor = ContentExtractor(max_chars=1000)
        
        with patch('utils.content_extractor.HAS_TRAFILATURA', False):
            with patch('utils.content_extractor.HAS_BS4', True):
                result = extractor.extract_content(mock_html_content, "https://example.com/test")
                
                assert result["status"] == "success"
                assert "beautifulsoup" in result["method"]
                assert "Introduction to Web Scraping" in result["content"]
    
    def test_content_extractor_basic_fallback(self, mock_html_content):
        """Test ContentExtractor basic text extraction fallback"""
        extractor = ContentExtractor(max_chars=1000)
        
        with patch('utils.content_extractor.HAS_TRAFILATURA', False):
            with patch('utils.content_extractor.HAS_BS4', False):
                result = extractor.extract_content(mock_html_content, "https://example.com/test")
                
                assert result["status"] == "success"
                assert "basic" in result["method"]
                assert len(result["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_polite_content_extractor(self, mock_html_content):
        """Test PoliteContentExtractor integration"""
        config = SmartExtractionConfig(
            max_urls=2,
            max_chars_per_url=1000,
            max_total_chars=2000,
            request_delay=0.1  # Faster for testing
        )
        extractor = PoliteContentExtractor(config)
        
        with patch.object(WebFetcher, 'fetch_content') as mock_fetch:
            mock_fetch.return_value = {
                "status": "success",
                "content": mock_html_content,
                "url": "https://example.com/test",
                "status_code": 200,
                "content_type": "text/html",
                "content_length": len(mock_html_content),
                "fetch_time": 0.5
            }
            
            result = await extractor.extract_from_url("https://example.com/test", "Test Title")
            
            assert result["status"] == "success"
            assert result["title"] == "Test Title"
            assert len(result["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_smart_search_extract_success(self, mock_search_results, mock_html_content):
        """Test complete smart_search_extract workflow"""
        with patch('server_search.web_search') as mock_web_search:
            with patch.object(PoliteContentExtractor, 'extract_from_url') as mock_extract:
                mock_web_search.return_value = mock_search_results
                mock_extract.return_value = {
                    "status": "success",
                    "url": "https://example.com/test",
                    "title": "Test Title",
                    "content": "This is extracted content from the webpage.",
                    "content_length": 45,
                    "extraction_method": "trafilatura",
                    "fetch_time": 0.5
                }
                
                result = await smart_search_extract("python web scraping", max_urls=2)
                
                assert result["status"] == "success"
                assert "python web scraping" in result["message"]
                assert len(result["extracted_content"]) > 0
                assert result["extraction_stats"]["successful_extractions"] > 0
    
    @pytest.mark.asyncio
    async def test_smart_search_extract_empty_query(self):
        """Test smart_search_extract with empty query"""
        result = await smart_search_extract("")
        
        assert result["status"] == "error"
        assert "Missing required parameter" in result["message"]
    
    @pytest.mark.asyncio
    async def test_smart_search_extract_search_failure(self):
        """Test smart_search_extract when web search fails"""
        with patch('server_search.web_search') as mock_web_search:
            mock_web_search.return_value = {
                "status": "error",
                "message": "Search API failed"
            }
            
            result = await smart_search_extract("test query")
            
            assert result["status"] == "error"
            assert "Search API failed" in result["message"]
    
    @pytest.mark.asyncio
    async def test_extraction_with_partial_failures(self, mock_search_results):
        """Test extraction handling partial failures"""
        with patch('server_search.web_search') as mock_web_search:
            with patch.object(PoliteContentExtractor, 'extract_from_url') as mock_extract:
                mock_web_search.return_value = mock_search_results
                
                # Mock mixed success/failure results
                mock_extract.side_effect = [
                    {
                        "status": "success",
                        "url": "https://example.com/test1",
                        "title": "Success Title",
                        "content": "Successful extraction",
                        "content_length": 20
                    },
                    {
                        "status": "error",
                        "url": "https://example.com/test2",
                        "title": "Failed Title",
                        "content": "",
                        "error": "Failed to fetch content"
                    }
                ]
                
                result = await smart_search_extract("test query", max_urls=2)
                
                assert result["status"] == "success"
                assert result["extraction_stats"]["urls_processed"] == 2
                assert result["extraction_stats"]["successful_extractions"] == 1
    
    def test_smart_extraction_config(self):
        """Test SmartExtractionConfig with environment variables"""
        config = SmartExtractionConfig()
        
        assert config.max_urls == 3  # Default value
        assert config.max_chars_per_url == 2000  # Default value
        assert config.max_total_chars == 5000  # Default value
        assert config.request_delay == 1.0  # Default value
        assert "OhSee-AI-Assistant" in config.user_agent

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
