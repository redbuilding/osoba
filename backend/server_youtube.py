# server_youtube.py  – resilient YouTube transcript MCP server (YT‑API 1.0.3)
from __future__ import annotations

import html
import json
import logging
import os
import re
import tempfile
import time
from contextlib import contextmanager
from typing import Iterable
from urllib.parse import parse_qs, urlparse

import requests
import yt_dlp
from fastmcp import FastMCP
from pytube import YouTube
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
logging.getLogger("pytube").setLevel(logging.INFO) # Pytube can be very noisy

# ──────────────────────────── constants ─────────────────────────────
# NOTE: This implementation uses a multi-library approach for maximum reliability.
# It attempts to fetch transcripts using youtube-transcript-api, Pytube, and yt-dlp.
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


def _fetch_with_pytube(video_id: str) -> str:
    """Fetches a transcript using the Pytube library."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
    yt.bypass_age_gate()  # Recommended for age-restricted content

    caption = yt.captions.get_by_language_code('en')
    if not caption:
        raise RuntimeError("Pytube: No English captions found.")

    srt = caption.generate_srt_captions()
    if not srt:
        raise RuntimeError("Pytube: Failed to generate SRT captions.")

    # Strip timestamps and formatting from SRT
    plain = re.sub(r'\d+\n\d{2}:\d{2}:\d{2}[.,]\d{3} --> .*?\n', '', srt)
    plain = html.unescape(re.sub(r'\n{2,}', '\n', plain)).strip()
    return plain


def _fetch_with_ytdlp(video_id: str) -> str:
    """
    Fetches a transcript using the yt-dlp library, handling both VTT
    and JSON transcript formats.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "vtt",
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        tracks = info.get("subtitles", {}).get("en") or info.get(
            "automatic_captions", {}
        ).get("en")
        if not tracks:
            raise RuntimeError("yt-dlp: No English captions found.")

        # The URL can point to either a VTT file or a JSON object
        transcript_url = tracks[0]["url"]

    response_text = requests.get(transcript_url, timeout=30).text
    if not response_text:
        raise RuntimeError("yt-dlp: Failed to download transcript content.")

    try:
        # Attempt to parse as JSON (the newer format)
        data = json.loads(response_text)
        if 'events' in data:
            segments = []
            for event in data.get('events', []):
                for seg in event.get('segs', []):
                    segments.append(seg.get('utf8', ''))

            # Join all segments, then normalize whitespace.
            full_text = "".join(segments).replace('\n', ' ').strip()
            # Collapse multiple spaces into one
            clean_text = re.sub(r'\s+', ' ', full_text)
            return clean_text
    except json.JSONDecodeError:
        # If JSON parsing fails, assume it's the older VTT format
        logger.debug("yt-dlp response is not JSON, parsing as VTT.")
        plain = re.sub(r'^\s*WEBVTT.*?\n', '', response_text, flags=re.DOTALL)
        plain = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> .*?\n', '', plain)
        plain = html.unescape(re.sub(r'\n{2,}', '\n', plain)).strip()
        return plain

    # If it was JSON but didn't have 'events', it's an unknown format
    raise RuntimeError("yt-dlp: Unknown transcript format.")


def _fetch_with_yta(video_id: str, cookie_path: str | None = None, proxy: str | None = None) -> str:
    """Internal helper to fetch transcript using youtube-transcript-api."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    kwargs = {"http_client": session}
    if cookie_path:
        kwargs["cookie_path"] = cookie_path
    if proxy:
        kwargs["proxy_config"] = GenericProxyConfig(https_url=proxy)

    api_instance = YouTubeTranscriptApi(**kwargs)
    tlist = api_instance.list(video_id)
    transcript = _pick_transcript(tlist)
    content = transcript.fetch()
    return _join_transcript(content)


# ───────────────────────── core fetch logic ─────────────────────────
def _fetch_transcript(video_id: str) -> str:
    """
    Fetches a transcript for a given video ID, trying different strategies.

    Strategy order:
      1. youtube-transcript-api (default)
      2. youtube-transcript-api (with cookie)
      3. Pytube
      4. yt-dlp
      5. youtube-transcript-api (with proxy)

    Raises CouldNotRetrieveTranscript if all attempts fail.
    """
    # Attempt 1: youtube-transcript-api (default)
    try:
        logger.debug("Attempt 1: Fetching with youtube-transcript-api (default)")
        return _fetch_with_yta(video_id)
    except Exception as e:
        logger.warning("Attempt 1 (yta-default) failed for %s: %s", video_id, e)

    # Attempt 2: youtube-transcript-api (with cookie)
    try:
        logger.debug("Attempt 2: Fetching with youtube-transcript-api (cookie)")
        with _temp_cookie_file() as cookie_path:
            return _fetch_with_yta(video_id, cookie_path=cookie_path)
    except Exception as e:
        logger.warning("Attempt 2 (yta-cookie) failed for %s: %s", video_id, e)

    # Attempt 3: Pytube
    try:
        logger.debug("Attempt 3: Fetching with Pytube")
        return _fetch_with_pytube(video_id)
    except Exception as e:
        logger.warning("Attempt 3 (Pytube) failed for %s: %s", video_id, e)

    # Attempt 4: yt-dlp
    try:
        logger.debug("Attempt 4: Fetching with yt-dlp")
        return _fetch_with_ytdlp(video_id)
    except Exception as e:
        logger.warning("Attempt 4 (yt-dlp) failed for %s: %s", video_id, e)

    # Attempt 5: youtube-transcript-api (with proxy)
    proxy = os.getenv("YTA_PROXY")
    if proxy:
        try:
            logger.debug("Attempt 5: Fetching with youtube-transcript-api (proxy)")
            return _fetch_with_yta(video_id, proxy=proxy)
        except Exception as e:
            logger.warning("Attempt 5 (yta-proxy) failed for %s: %s", video_id, e)

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
        # Provide a more helpful error message if the proxy wasn't used.
        if not os.getenv("YTA_PROXY"):
            return (
                f"Error: Failed to retrieve transcript for '{vid}'. This can happen "
                "with IP-based blocking. Please try again later or configure the "
                "YTA_PROXY environment variable to use a proxy server."
            )
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
