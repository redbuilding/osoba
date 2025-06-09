# server_youtube.py  – resilient YouTube transcript MCP server (YT‑API 1.0.3)
from __future__ import annotations

import logging
import os
import tempfile
import time
from contextlib import contextmanager
from typing import Iterable
from urllib.parse import parse_qs, urlparse

from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)
from youtube_transcript_api._transcripts import TranscriptList
from youtube_transcript_api.proxies import GenericProxyConfig

# ───────────────────────────── logging ──────────────────────────────
logging.basicConfig(
    level=os.getenv("YTA_LOG_LEVEL", "DEBUG"),
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
)
logger = logging.getLogger("YouTubeTranscriptServer")
logging.getLogger("youtube_transcript_api").setLevel(logging.DEBUG)

# ──────────────────────────── constants ─────────────────────────────
# NOTE: This implementation assumes a modern version of youtube-transcript-api
# which supports instance-based configuration for cookies and proxies.
# Intermittent failures are often due to YouTube's consent requirements or
# bot detection, which we attempt to solve by providing a consent cookie and
# a browser-like User-Agent.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
)
CONSENT_COOKIE = {"name": "CONSENT", "value": "YES+cb.20240402-18-0"}
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


@contextmanager
def _temp_cookie_file():
    """Creates a temporary Netscape-formatted cookie file for consent."""
    # A valid future expiration timestamp is required for the cookie to be accepted.
    expiration = int(time.time()) + 31536000  # 1 year in the future
    cookie_content = (
        "# Netscape HTTP Cookie File\n"
        ".youtube.com\tTRUE\t/\tTRUE\t{expiration}\t{name}\t{value}\n"
    ).format(
        expiration=expiration,
        name=CONSENT_COOKIE["name"],
        value=CONSENT_COOKIE["value"],
    )

    filepath = None
    try:
        # Suffix is important for the library to recognize it as a text file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as f:
            f.write(cookie_content)
            filepath = f.name
        logger.debug("Created temporary cookie file at %s", filepath)
        yield filepath
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            logger.debug("Removed temporary cookie file at %s", filepath)


def _pick_transcript(tlist: TranscriptList, pref_langs: Iterable[str] = LANG_PREF):
    """Choose a transcript: first preferred language, else first available."""
    try:
        return tlist.find_transcript(pref_langs)
    except NoTranscriptFound:
        # Fallback to the first transcript in the list if preferred langs aren't found
        return next(iter(tlist))


def _try_fetch_with_instance(api_instance: YouTubeTranscriptApi, video_id: str) -> str:
    """
    Perform the full list -> pick -> fetch sequence with a given API instance,
    after setting a browser-like User-Agent.
    """
    # Set a browser-like User-Agent to avoid being blocked.
    api_instance.http_client.headers.update({"User-Agent": USER_AGENT})

    tlist = api_instance.list(video_id)
    transcript = _pick_transcript(tlist)
    content = transcript.fetch()
    return _join_transcript(content)


# ───────────────────────── core fetch logic ─────────────────────────
def _fetch_transcript(video_id: str) -> str:
    """
    Fetches a transcript for a given video ID, trying different strategies.

    Strategy order:
      1. Default instance (no cookies/proxy)
      2. Instance with CONSENT cookie file
      3. Instance with proxy (if YTA_PROXY is set)

    Raises CouldNotRetrieveTranscript if all attempts fail.
    """
    # Attempt 1: Default instance
    try:
        logger.debug("Attempt 1: Fetching transcript for %s (default)", video_id)
        return _try_fetch_with_instance(YouTubeTranscriptApi(), video_id)
    except Exception as e:
        logger.warning("Attempt 1 failed for %s: %s", video_id, e)

    # Attempt 2: Instance with CONSENT cookie
    try:
        logger.debug("Attempt 2: Fetching transcript for %s (with cookie file)", video_id)
        with _temp_cookie_file() as cookie_path:
            api_with_cookie = YouTubeTranscriptApi(cookie_path=cookie_path)
            return _try_fetch_with_instance(api_with_cookie, video_id)
    except Exception as e:
        logger.warning("Attempt 2 (cookie) failed for %s: %s", video_id, e)

    # Attempt 3: Instance with proxy
    proxy = os.getenv("YTA_PROXY")
    if proxy:
        try:
            logger.debug("Attempt 3: Fetching transcript for %s (with proxy)", video_id)
            proxy_config = GenericProxyConfig(https_url=proxy)
            api_with_proxy = YouTubeTranscriptApi(proxy_config=proxy_config)
            return _try_fetch_with_instance(api_with_proxy, video_id)
        except Exception as e:
            logger.warning("Attempt 3 (proxy) failed for %s: %s", video_id, e)

    # If all attempts fail, raise the specific error
    raise CouldNotRetrieveTranscript(video_id)

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
    except Exception as exc:
        logger.exception("Unhandled error while processing %s", youtube_url)
        return f"An unexpected error occurred: {exc}"

# ──────────────────────────── entrypoint ────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
