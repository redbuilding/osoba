"""Parse uploaded files and URLs into plain text."""
from typing import Tuple
from core.config import get_logger

logger = get_logger("document_parser")

MAX_DOCUMENT_CHARS = 200_000


def parse_file(filename: str, content_bytes: bytes) -> Tuple[str, str]:
    """Parse file bytes into plain text.

    Args:
        filename: Original filename (used to detect type)
        content_bytes: Raw file bytes

    Returns:
        Tuple of (text, file_type)

    Raises:
        ValueError: If file type is unsupported or content exceeds max size
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "txt":
        text = content_bytes.decode("utf-8", errors="replace")
        file_type = "txt"

    elif ext == "md":
        text = content_bytes.decode("utf-8", errors="replace")
        file_type = "md"

    elif ext == "docx":
        text = _parse_docx(content_bytes)
        file_type = "docx"

    elif ext == "pdf":
        text = _parse_pdf(content_bytes)
        file_type = "pdf"

    else:
        raise ValueError(f"Unsupported file type: .{ext}. Supported: txt, md, docx, pdf")

    if len(text) > MAX_DOCUMENT_CHARS:
        raise ValueError(
            f"Document too large: {len(text):,} chars (max {MAX_DOCUMENT_CHARS:,}). "
            "Please upload a smaller document or split it into parts."
        )

    return text.strip(), file_type


def parse_url(url: str) -> str:
    """Fetch and extract plain text from a URL using trafilatura.

    Args:
        url: URL to fetch

    Returns:
        Extracted plain text

    Raises:
        ValueError: If URL cannot be fetched or content exceeds max size
    """
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise ValueError(f"Failed to fetch URL: {url}")

        text = trafilatura.extract(downloaded)
        if not text:
            raise ValueError(f"No text content extracted from URL: {url}")

        if len(text) > MAX_DOCUMENT_CHARS:
            raise ValueError(
                f"URL content too large: {len(text):,} chars (max {MAX_DOCUMENT_CHARS:,})."
            )

        return text.strip()
    except ImportError:
        raise ValueError("trafilatura is not installed. Cannot fetch URLs.")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Error fetching URL: {e}")


def _parse_docx(content_bytes: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        import io
        from docx import Document
        doc = Document(io.BytesIO(content_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as e:
        raise ValueError(f"Failed to parse DOCX: {e}")


def _parse_pdf(content_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    try:
        import io
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        if not text_parts:
            raise ValueError("No text extracted from PDF. The PDF may be scanned/image-based.")
        return "\n\n".join(text_parts)
    except ImportError:
        raise ValueError("pdfplumber is not installed. Cannot parse PDF files.")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {e}")
