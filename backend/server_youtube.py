from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from urllib.parse import urlparse, parse_qs

# Initialize the FastMCP Server
mcp = FastMCP("YouTubeTranscriptServer")

def _extract_video_id(url: str) -> str | None:
    """Helper function to extract video ID from various YouTube URL formats."""
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            p = parse_qs(parsed_url.query)
            return p.get('v', [None])[0]
        if parsed_url.path.startswith('/embed/'):
            return parsed_url.path.split('/embed/')[1]
    return None

@mcp.tool()
def get_youtube_transcript(youtube_url: str) -> str:
    """
    Fetches the transcript for a given YouTube video URL.

    Args:
        youtube_url: The full URL of the YouTube video.

    Returns:
        The full transcript as a single string of text, or an error message if it cannot be retrieved.
    """
    video_id = _extract_video_id(youtube_url)

    if not video_id:
        return f"Error: Could not extract a valid YouTube video ID from the URL provided: {youtube_url}"

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([item['text'] for item in transcript_list])
        return transcript_text
    except TranscriptsDisabled:
        return f"Error: Transcripts are disabled for the video with ID '{video_id}'."
    except NoTranscriptFound:
        return f"Error: No transcript could be found for the video with ID '{video_id}'. The video may not have transcripts or they might not be available in a supported language."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

if __name__ == "__main__":
    # Run the server, listening on stdio
    mcp.run(transport="stdio")