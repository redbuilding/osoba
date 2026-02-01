import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from utils.content_extractor import ContentExtractor

class TestContentExtractor:
    """Test suite for content extraction utilities"""
    
    @pytest.fixture
    def sample_html(self):
        """Sample HTML content for testing"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Article Title</title>
            <meta name="description" content="This is a test article description">
        </head>
        <body>
            <nav>Navigation menu</nav>
            <header>Site header</header>
            <main>
                <article>
                    <h1>Main Article Heading</h1>
                    <p>This is the first paragraph of the article with some meaningful content.</p>
                    <h2>Section Heading</h2>
                    <p>This is another paragraph with more detailed information about the topic.</p>
                    <p>A third paragraph with additional context and examples.</p>
                    <div class="sidebar">Sidebar content that should be ignored</div>
                </article>
            </main>
            <footer>Site footer</footer>
            <script>console.log('This script should be removed');</script>
        </body>
        </html>
        """
    
    @pytest.fixture
    def malformed_html(self):
        """Malformed HTML for testing robustness"""
        return """
        <html>
        <head><title>Malformed HTML</title>
        <body>
        <h1>Unclosed heading
        <p>Paragraph without closing tag
        <div>Nested <span>content</span> with &amp; entities &lt;test&gt;
        """
    
    @pytest.fixture
    def minimal_html(self):
        """Minimal HTML content"""
        return "<html><body><p>Just a simple paragraph.</p></body></html>"
    
    def test_clean_text_basic(self):
        """Test basic text cleaning functionality"""
        extractor = ContentExtractor()
        
        dirty_text = "  This   has   extra   spaces  \n\n\n  and newlines  "
        clean_text = extractor.clean_text(dirty_text)
        
        assert clean_text == "This has extra spaces and newlines"
    
    def test_clean_text_html_entities(self):
        """Test HTML entity cleaning"""
        extractor = ContentExtractor()
        
        text_with_entities = "This &amp; that &lt;tag&gt; &quot;quoted&quot; &#39;apostrophe&#39; &nbsp;space"
        clean_text = extractor.clean_text(text_with_entities)
        
        assert clean_text == "This & that <tag> \"quoted\" 'apostrophe' space"
    
    def test_clean_text_empty_input(self):
        """Test clean_text with empty input"""
        extractor = ContentExtractor()
        
        assert extractor.clean_text("") == ""
        assert extractor.clean_text(None) == ""
        assert extractor.clean_text("   ") == ""
    
    def test_extract_with_trafilatura_success(self, sample_html):
        """Test successful extraction with trafilatura"""
        extractor = ContentExtractor(max_chars=1000)
        
        with patch('utils.content_extractor.HAS_TRAFILATURA', True):
            with patch('trafilatura.extract') as mock_extract:
                with patch('trafilatura.extract_metadata') as mock_metadata:
                    mock_extract.return_value = "This is the extracted main content from trafilatura."
                    
                    mock_meta = MagicMock()
                    mock_meta.title = "Test Article Title"
                    mock_meta.author = "Test Author"
                    mock_meta.date = "2024-01-01"
                    mock_meta.description = "Test description"
                    mock_metadata.return_value = mock_meta
                    
                    result = extractor.extract_with_trafilatura(sample_html, "https://example.com")
                    
                    assert result is not None
                    assert result["method"] == "trafilatura"
                    assert result["content"] == "This is the extracted main content from trafilatura."
                    assert result["title"] == "Test Article Title"
                    assert result["author"] == "Test Author"
    
    def test_extract_with_trafilatura_failure(self, sample_html):
        """Test trafilatura extraction failure"""
        extractor = ContentExtractor()
        
        with patch('utils.content_extractor.HAS_TRAFILATURA', True):
            with patch('trafilatura.extract') as mock_extract:
                mock_extract.return_value = None  # Simulate extraction failure
                
                result = extractor.extract_with_trafilatura(sample_html)
                
                assert result is None
    
    def test_extract_with_trafilatura_not_available(self, sample_html):
        """Test when trafilatura is not available"""
        extractor = ContentExtractor()
        
        with patch('utils.content_extractor.HAS_TRAFILATURA', False):
            result = extractor.extract_with_trafilatura(sample_html)
            
            assert result is None
    
    def test_extract_with_beautifulsoup_success(self, sample_html):
        """Test successful extraction with BeautifulSoup"""
        extractor = ContentExtractor(max_chars=1000)
        
        with patch('utils.content_extractor.HAS_BS4', True):
            result = extractor.extract_with_beautifulsoup(sample_html)
            
            assert result is not None
            assert result["method"] == "beautifulsoup"
            assert "Main Article Heading" in result["content"]
            assert "first paragraph" in result["content"]
            assert result["title"] == "Test Article Title"
            assert result["headings_found"] > 0
            assert result["paragraphs_found"] > 0
    
    def test_extract_with_beautifulsoup_malformed_html(self, malformed_html):
        """Test BeautifulSoup with malformed HTML"""
        extractor = ContentExtractor(max_chars=1000)
        
        with patch('utils.content_extractor.HAS_BS4', True):
            result = extractor.extract_with_beautifulsoup(malformed_html)
            
            assert result is not None
            assert result["method"] == "beautifulsoup"
            assert len(result["content"]) > 0
    
    def test_extract_with_beautifulsoup_not_available(self, sample_html):
        """Test when BeautifulSoup is not available"""
        extractor = ContentExtractor()
        
        with patch('utils.content_extractor.HAS_BS4', False):
            result = extractor.extract_with_beautifulsoup(sample_html)
            
            assert result is None
    
    def test_extract_content_trafilatura_primary(self, sample_html):
        """Test extract_content using trafilatura as primary method"""
        extractor = ContentExtractor(max_chars=500)
        
        with patch('utils.content_extractor.HAS_TRAFILATURA', True):
            with patch('trafilatura.extract') as mock_extract:
                with patch('trafilatura.extract_metadata') as mock_metadata:
                    mock_extract.return_value = "Trafilatura extracted content"
                    mock_metadata.return_value = MagicMock(title="Test Title")
                    
                    result = extractor.extract_content(sample_html, "https://example.com")
                    
                    assert result["status"] == "success"
                    assert "trafilatura" in result["method"]
                    assert result["content"] == "Trafilatura extracted content"
    
    def test_extract_content_beautifulsoup_fallback(self, sample_html):
        """Test extract_content falling back to BeautifulSoup"""
        extractor = ContentExtractor(max_chars=500)
        
        with patch('utils.content_extractor.HAS_TRAFILATURA', True):
            with patch('utils.content_extractor.HAS_BS4', True):
                with patch('trafilatura.extract') as mock_extract:
                    mock_extract.return_value = None  # Trafilatura fails
                    
                    result = extractor.extract_content(sample_html)
                    
                    assert result["status"] == "success"
                    assert "beautifulsoup" in result["method"]
                    assert len(result["content"]) > 0
    
    def test_extract_content_basic_fallback(self, sample_html):
        """Test extract_content using basic text extraction as last resort"""
        extractor = ContentExtractor(max_chars=500)
        
        with patch('utils.content_extractor.HAS_TRAFILATURA', False):
            with patch('utils.content_extractor.HAS_BS4', False):
                result = extractor.extract_content(sample_html)
                
                assert result["status"] == "success"
                assert result["method"] == "basic"
                assert len(result["content"]) > 0
                # Should not contain HTML tags
                assert "<" not in result["content"]
    
    def test_extract_content_empty_html(self):
        """Test extract_content with empty HTML"""
        extractor = ContentExtractor()
        
        result = extractor.extract_content("")
        
        assert result["status"] == "error"
        assert "Empty HTML content" in result["message"]
        assert result["content"] == ""
    
    def test_extract_content_character_limit(self, sample_html):
        """Test content extraction respects character limits"""
        extractor = ContentExtractor(max_chars=50)
        
        with patch('utils.content_extractor.HAS_TRAFILATURA', True):
            with patch('trafilatura.extract') as mock_extract:
                mock_extract.return_value = "This is a very long piece of content that should be truncated because it exceeds the maximum character limit set for the extractor."
                
                result = extractor.extract_content(sample_html)
                
                assert result["status"] == "success"
                assert len(result["content"]) <= 53  # 50 + "..."
                assert result["content"].endswith("...")
    
    def test_extract_content_all_methods_fail(self, sample_html):
        """Test when all extraction methods fail"""
        extractor = ContentExtractor()
        
        with patch('utils.content_extractor.HAS_TRAFILATURA', True):
            with patch('utils.content_extractor.HAS_BS4', True):
                with patch('trafilatura.extract') as mock_trafilatura:
                    with patch('utils.content_extractor.ContentExtractor.extract_with_beautifulsoup') as mock_bs4:
                        with patch('re.sub') as mock_re:
                            mock_trafilatura.return_value = None
                            mock_bs4.return_value = None
                            mock_re.side_effect = Exception("Regex failed")
                            
                            result = extractor.extract_content(sample_html)
                            
                            assert result["status"] == "error"
                            assert "Failed to extract content" in result["message"]
    
    def test_content_extractor_initialization(self):
        """Test ContentExtractor initialization with different parameters"""
        # Default initialization
        extractor1 = ContentExtractor()
        assert extractor1.max_chars == 2000
        
        # Custom max_chars
        extractor2 = ContentExtractor(max_chars=1000)
        assert extractor2.max_chars == 1000
    
    def test_content_extraction_with_minimal_html(self, minimal_html):
        """Test extraction with minimal HTML content"""
        extractor = ContentExtractor(max_chars=100)
        
        with patch('utils.content_extractor.HAS_TRAFILATURA', False):
            with patch('utils.content_extractor.HAS_BS4', True):
                result = extractor.extract_content(minimal_html)
                
                assert result["status"] == "success"
                assert "simple paragraph" in result["content"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
