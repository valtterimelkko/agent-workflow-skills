---
name: video-deep-understanding
description: "Deeply understand any video by extracting transcript evidence and visual evidence from a URL or local file. Use whenever the user pastes a video link or local video and wants analysis, summary, transcription, UI inspection, timestamped answers, comparison against local code/docs, or wants 'the part where they talk about X'. Make sure to use this skill for product demos, tutorials, screen recordings, and walkthrough videos even when the user does not explicitly ask for a transcript."
argument-hint: "<video-url-or-path> [question]"
allowed-tools: Bash, Read, AskUserQuestion
homepage: https://github.com/valtterimelkko/agent-workflow-skills
repository: https://github.com/valtterimelkko/agent-workflow-skills
author: valtterimelkko (based on work by bradautomates)
license: MIT
user-invocable: true
---

# Video Deep Understanding

This skill gives the agent a video input. It can:
- download a remote video or use a local file
- pull native captions when available
- fall back to OpenAI transcription when needed
- extract frames for visual inspection
- search the transcript for named concepts before burning image tokens
- reuse a cached local copy of a previously downloaded URL on follow-up runs

## Progressive disclosure

Read these only when needed:
- `references/quickstart.md` — default workflow and key flags
- `references/troubleshooting.md` — sharp edges, failure interpretation, and when to inspect scripts

Do **not** read bundled scripts by default. Inspect them only if setup/download/transcription fails repeatedly, output looks suspicious, or the user asks about internals.

## Step 0 — silent preflight

On macOS/Linux use `python3`. On Windows use `python` instead.

Run:

```bash
python3 scripts/setup.py --check
```

If it exits 0, say nothing and continue.

If it exits non-zero:
- `2` → missing binaries; run `python3 scripts/setup.py`
- `3` → missing OpenAI key; run installer and ask the user for the key if they want transcription fallback
- `4` → both missing; run installer, then ask for the key if needed

If you need more detail, use:

```bash
python3 scripts/setup.py --json
```

Useful fields include:
- `status`
- `missing_binaries`
- `has_api_key`
- `has_proxy`
- `js_runtimes`
- `cookies_available`

## Default invocation rule

For **long videos**, **UI demos**, or **concept-finding tasks**, prefer a transcript-first pass:

```bash
python3 scripts/watch.py "$URL" --transcript-only --find 'keyword|other keyword'
```

Then zoom into the relevant section:

```bash
python3 scripts/watch.py "$URL" --start 4:32 --end 5:16 --resolution 1024 --contact-sheet
```

For short videos where the user wants a broad summary, a direct full scan is fine:

```bash
python3 scripts/watch.py "$URL"
```

If you already watched the same video in this session and still have the relevant transcript/frames in context, answer directly instead of re-running.

## Important flags

- `--transcript-only` — skip frame extraction
- `--find REGEX` — show transcript matches and suggested focus windows
- `--start` / `--end` — focused visual pass
- `--resolution 1024` — better for reading on-screen UI text
- `--compact-report` — shorter report for agent workflows
- `--contact-sheet` — best-effort composite image of extracted frames
- `--no-transcribe` — disable OpenAI fallback

## Key behaviour changes to exploit

### 1. Transcript-first narrowing
If the user is asking about a named concept, workflow stage, UI element, or "the part where...", do **not** start with a sparse full-video frame scan on a long video. Search the transcript first.

### 2. Automatic cache reuse
Successful URL downloads are cached in the system temp directory. Follow-up runs on the same URL will reuse the cached local copy when possible. This reduces repeated YouTube failures and saves time.

### 3. Transcript match windows
When `--find` is used, the script emits:
- transcript matches
- suggested focus windows around those matches

Use those windows for the second pass.

## How to answer

Use two evidence streams:
- **Transcript evidence** — what is said, with timestamps
- **Visual evidence** — what is shown, with timestamps

For UI/tutorial tasks, explicitly separate:
- spoken explanation
- visible interface structure
- your interpretation/recommendation

## Long-video rule

If the video is over ~10 minutes:
- do not assume a full scan is enough for precise UI analysis
- prefer transcript-first narrowing
- then run focused windows only

## Security & data handling

What this skill does:
- downloads public video/caption data locally via `yt-dlp`
- extracts frames/audio locally via `ffmpeg` / `ffprobe`
- sends **audio only** to OpenAI transcription when fallback is needed and `OPENAI_API_KEY` is set
- stores temporary working files locally
- may reuse a cached local video copy for the same URL in later runs

What this skill does **not** do:
- does not upload the video itself to OpenAI
- does not log into websites automatically
- does not expose API keys in stdout/stderr
- does not require script inspection on every invocation

## When things go wrong

If YouTube starts failing, especially with bot-challenge or 403-style errors, read:
- `references/troubleshooting.md`

That file tells you when to:
- reuse cache
- rely on proxy/cookies
- inspect scripts
- stop retrying and explain the limitation clearly

## Cleanup

The script prints a work directory at the end of every run.
- Keep it if follow-up analysis is likely.
- Delete it when you are done.
