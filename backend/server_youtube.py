# server_youtube.py  – resilient YouTube transcript MCP server (YT‑API 1.0.3)
from __future__ import annotations

import logging
import os
from typing import Iterable
from urllib.parse import parse_qs, urlparse
from xml.etree.ElementTree import ParseError

from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

# ───────────────────────────── logging ──────────────────────────────
logging.basicConfig(
    level=os.getenv("YTA_LOG_LEVEL", "DEBUG"),
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
)
logger = logging.getLogger("YouTubeTranscriptServer")
logging.getLogger("youtube_transcript_api").setLevel(logging.DEBUG)

# ──────────────────────────── constants ─────────────────────────────
CONSENT_COOKIE = {"CONSENT": "YES+cb.20240402-18-0"}
LANG_PREF      = ("en", "en-US")   # preferred languages

# ──────────────────────── FastMCP server init ───────────────────────
mcp = FastMCP("YouTubeTranscriptServer")

# ───────────────────────── helper functions ─────────────────────────
def _extract_video_id(url: str) -> str | None:
    """Extract the YouTube video ID from share / watch / embed URLs."""
    parsed = urlparse(url)
    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")
    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if parsed.path.startswith("/embed/"):
            return parsed.path.split("/embed/")[1]
    return None


def _join_transcript(snips: Iterable) -> str:
    """Concatenate text from dicts or FetchedTranscriptSnippet objects."""
    return " ".join(
        s["text"] if isinstance(s, dict) else getattr(s, "text", "")
        for s in snips
    ).strip()


def _pick_transcript(tlist, pref_langs: Iterable[str] = LANG_PREF):
    """Choose a transcript: first preferred language, else first available."""
    try:
        return tlist.find_transcript(pref_langs)
    except NoTranscriptFound:
        return next(iter(tlist))

# ───────────────────────── core fetch logic ─────────────────────────
def _fetch_transcript(video_id: str) -> str:
    """
    Fetches a transcript for a given video ID, trying different strategies based on the modern
    youtube-transcript-api v1.x instance-based API.

    Strategy order:
      1. Default (no cookies/proxy)
      2. With CONSENT cookie
      3. With proxy (if YTA_PROXY is set)

    Raises CouldNotRetrieveTranscript if all attempts fail.
    """
    tlist = None

    # Attempt 1: Default instance
    try:
        logger.debug("Attempt 1: Fetching list for %s (default)", video_id)
        tlist = YouTubeTranscriptApi().list(video_id)
    except Exception as e:
        logger.warning("Attempt 1 failed for %s: %s", video_id, e)

    # Attempt 2: Instance with CONSENT cookie
    if not tlist:
        try:
            logger.debug("Attempt 2: Fetching list for %s (with cookie)", video_id)
            api_with_cookie = YouTubeTranscriptApi(cookies=CONSENT_COOKIE)
            tlist = api_with_cookie.list(video_id)
        except Exception as e:
            logger.warning("Attempt 2 (cookie) failed for %s: %s", video_id, e)

    # Attempt 3: Instance with proxy
    if not tlist:
        proxy = os.getenv("YTA_PROXY")
        if proxy:
            try:
                logger.debug("Attempt 3: Fetching list for %s (with proxy)", video_id)
                api_with_proxy = YouTubeTranscriptApi(proxies={"https": proxy})
                tlist = api_with_proxy.list(video_id)
            except Exception as e:
                logger.warning("Attempt 3 (proxy) failed for %s: %s", video_id, e)

    if not tlist:
        raise CouldNotRetrieveTranscript(video_id)

    # If a list was retrieved, pick the best transcript and fetch its content
    transcript = _pick_transcript(tlist)
    return _join_transcript(transcript.fetch())

# ─────────────────────────── MCP tool API ───────────────────────────
@mcp.tool()
def get_youtube_transcript(youtube_url: str) -> str:
    """Return the transcript text for the given YouTube URL, or an error."""
    vid = _extract_video_id(youtube_url)
    if not vid:
        return f"Error: Could not extract a video ID from '{youtube_url}'."

    try:
        txt = _fetch_transcript(vid)
        return txt or f"Error: Transcript for '{vid}' was empty."

    except TranscriptsDisabled:
        return f"Error: Transcripts are disabled for video ID '{vid}'."
    except NoTranscriptFound:
        return (
            f"Error: No transcript available for video ID '{vid}'. "
            "The video may lack captions or they are restricted."
        )
    except CouldNotRetrieveTranscript:
        return (
            f"Error: Unable to retrieve a transcript for '{vid}' after multiple attempts. "
            "The video may be region‑blocked or YouTube may be throttling this server."
        )
    except ParseError:
        return (
            f"Error: YouTube returned malformed caption data for ID '{vid}'. "
            "Try again later."
        )
    except Exception as exc:
        logger.exception("Unhandled error while processing %s", youtube_url)
        return f"An unexpected error occurred: {exc}"

# ──────────────────────────── entrypoint ────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
