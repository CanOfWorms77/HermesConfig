---
name: youtube-content
description: Fetch YouTube video transcripts and transform them into structured content (chapters, summaries, threads, blog posts).
---

# YouTube Content Tool

Extract transcripts from YouTube videos and convert them into useful formats.

## Setup

```bash
pip install youtube-transcript-api
```

## Helper script

This skill includes `fetch_transcript.py` — use it to fetch transcripts quickly:

```bash
# JSON output with metadata
python3 SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID"

# With timestamps
python3 SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID" --timestamps

# Plain text output (good for piping into further processing)
python3 SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID" --text-only

# Specific language with fallback
python3 SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID" --language tr,en

# Timestamped plain text
python3 SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID" --text-only --timestamps
```

`SKILL_DIR` is the directory containing this SKILL.md file.

## URL formats supported

The script accepts any of these formats (or a raw 11-character video ID):

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://youtube.com/shorts/VIDEO_ID`
- `https://youtube.com/embed/VIDEO_ID`
- `https://youtube.com/live/VIDEO_ID`

## Output formats

After fetching the transcript, format it based on what the user asks for:

## Error handling

- **Transcript disabled**: Some videos have transcripts turned off — tell the user
- **Private/unavailable**: The API will raise an error — relay it clearly
- **No matching language**: Try without specifying a language to get whatever's available
- **Dependency missing**: On Debian/Ubuntu (e.g. Hetzner), run `pip install --break-system-packages youtube-transcript-api`
- **YouTube blocks cloud IPs**: If you get a "YouTube is blocking requests from your IP" error (common on Hetzner, AWS, GCP), use fallback strategies below.

## Fallbacks when youtube-transcript-api is blocked

When running from a cloud VPS (Hetzner, AWS, etc.), YouTube blocks the youtube-transcript-api. Try these in order:

### 1. Browser screenshot + Perplexity Sonar search
If transcript extraction fails, use Perplexity Sonar API to search for video recaps, reviews, and summaries:

```bash
# Read API key from env
API_KEY=$(grep PERPLEXITY_API_KEY ~/.hermes/.env | cut -d= -f2)

# Then send a query to Perplexity asking for a summary of the video
curl -s https://api.perplexity.ai/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sonar",
    "messages": [{"role": "user", "content": "Summarize this YouTube video: [describe video, include title and video ID]"}],
    "max_tokens": 1000
  }'
```

### 2. Try alternative transcript endpoints
Before falling back fully, try scraping caption tracks from the raw HTML page (no API library needed). Caption tracks may be available even when the transcript API is blocked. Parse `ytInitialPlayerResponse` for `captionTracks`.

### 3. DuckDuckGo + web search
Search for "[video title] summary", "[channel name] [video title] recap" to find articles, Reddit threads, or other sources that describe the video content.

## Workflow

1. Fetch the transcript using the helper script
2. **If blocked by YouTube** → Try caption track scraping from HTML → Then Perplexity Sonar → Then web search
3. If the transcript is very long (>50K chars), summarize in chunks
4. Transform into the requested output format using your own reasoning

## Error handling

- **Transcript disabled**: Some videos have transcripts turned off — tell the user
- **Private/unavailable**: The API will raise an error — relay it clearly
- **No matching language**: Try without specifying a language to get whatever's available
- **Dependency missing**: Run `pip install youtube-transcript-api` first
