# Video Deep Understanding

Give any agent the ability to deeply understand any video.

This skill downloads videos, extracts auto-scaled frames, pulls transcripts from native captions (or OpenAI's gpt-4o-transcribe API fallback), and hands frames + transcript to the agent so it can answer questions grounded in what's actually on screen and in the audio.

## What it does

1. **You paste a video and a question.** URL (anything yt-dlp supports — YouTube, Loom, TikTok, X, Instagram, plus hundreds more) or a local path (`.mp4`, `.mov`, `.mkv`, `.webm`).
2. **`yt-dlp` downloads it.** For URLs, into a temp working directory. For local files, no download — just probed in place.
3. **`ffmpeg` extracts frames at an auto-scaled rate.** The frame budget is duration-aware: ≤30s gets ~30 frames, 30-60s gets ~40, 1-3min gets ~60, 3-10min gets ~80, longer gets 100 sparsely. Hard ceilings: 2 fps, 100 frames. JPEGs at 512px wide by default.
4. **The transcript comes from one of two places.** First try: `yt-dlp` pulls native captions (manual or auto-generated) from the source. Free, instant. Fallback: extract a mono 16 kHz audio clip and send it to OpenAI's `/v1/audio/transcriptions` endpoint with `model=gpt-4o-transcribe` — the same endpoint the voicenotebot streaming-dictation project uses, but with the higher-quality model. If that fails, it silently falls back to `gpt-4o-mini-transcribe`.
5. **Frames + transcript are handed to the agent.** The script prints frame paths with `t=MM:SS` markers and the transcript with timestamps. The agent reads each frame in parallel — JPEGs render directly as images in its context.
6. **The agent answers grounded in what's actually on screen and in the audio.** Not "based on the description" or "according to the title." It saw the frames. It heard the transcript. It answers the way someone who watched the video would.

## Install

Clone into your agent's skills directory:

```bash
git clone https://github.com/valtterimelkko/agent-workflow-skills.git
cd .skills-global/video-deep-understanding
```

Or copy the `video-deep-understanding/` folder into your agent's skills path.

Zero config to start — `yt-dlp` and `ffmpeg` install on first run via `brew` on macOS (Linux/Windows print exact commands). Captions cover most public videos for free. An OpenAI API key is only needed when a video has no captions.

## API Key

The skill loads `OPENAI_API_KEY` via the shared credential loader (same pattern as other skills in this repo):

1. Environment variable `OPENAI_API_KEY`
2. `OPENAI_API_KEY` in a shell startup file such as `~/.bashrc`
3. `~/.config/video-deep-understanding/.env` file

To scaffold the config file:
```bash
python3 scripts/setup.py
```

## Residential Proxy (optional)

If your IP has been flagged by YouTube and downloads are failing with bot-protection errors, you can route yt-dlp through a residential proxy. Uses the **exact same pattern** as the `youtube-caption` skill in this repo:

```bash
export VIDEO_PROXY_URL="http://username:password@host:port"
# legacy fallback also supported:
export REDDIT_PROXY_URL="http://username:password@host:port"
```

Add this to your environment or a shell startup file such as `~/.bashrc`. `scripts/download.py` loads it via the shared credential hierarchy and passes it to yt-dlp via `--proxy` plus `HTTP_PROXY`/`HTTPS_PROXY` env vars.

## Usage

From the skill directory, run:

```bash
python3 scripts/watch.py "https://youtu.be/dQw4w9WgXcQ"
python3 scripts/watch.py ~/Movies/screen-recording.mp4
python3 scripts/watch.py "$URL" --start 2:15 --end 2:45
```

Flags:
- `--start T` / `--end T` — focus on a section
- `--max-frames N` — lower the cap for tighter token budget
- `--resolution W` — bump frame width to 1024 px when reading on-screen text
- `--fps F` — override auto-fps (still capped at 2 fps)
- `--no-transcribe` — disable transcription fallback; frames-only when no captions
- `--out-dir DIR` — keep working files somewhere specific

## Structure

```
video-deep-understanding/
├── SKILL.md              # skill contract
├── scripts/
│   ├── watch.py          # entry point — orchestrates download → frames → transcript
│   ├── download.py       # yt-dlp wrapper
│   ├── frames.py         # ffmpeg frame extraction + auto-fps logic
│   ├── transcribe.py     # VTT parsing + dedupe
│   ├── whisper.py        # OpenAI gpt-4o-transcribe client (pure stdlib)
│   └── setup.py          # preflight + installer
└── LICENSE
```

## Bring your own keys

| Capability | What you need | Cost |
|------------|---------------|------|
| Download + native captions | `yt-dlp` + `ffmpeg` | Free |
| Transcription fallback | [OpenAI API key](https://platform.openai.com/api-keys) — `gpt-4o-transcribe` | Standard OpenAI audio pricing |
| Disable fallback | `--no-transcribe` | Free, frames-only when no captions |

## License

MIT — based on work by bradautomates.
