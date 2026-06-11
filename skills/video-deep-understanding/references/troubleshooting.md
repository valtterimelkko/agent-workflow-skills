# Video Deep Understanding — Troubleshooting

## Known sharp edges

- Repeated YouTube URL re-runs can fail with **403 Forbidden** even after one successful run.
  - Prefer the automatic cached local copy after the first success.
- Some YouTube environments show **"Sign in to confirm you're not a bot"**.
  - Residential proxy and/or cookies may be needed.
- Missing JS runtime reduces yt-dlp reliability on YouTube.
  - `node`, `bun`, or `deno` improve extraction reliability.
- UI-heavy videos often need `--resolution 1024`.
- Long videos should usually not be frame-scanned in full.

## When to inspect scripts

Do **not** read bundled scripts by default.
Inspect them only when:
- setup fails
- download/transcription repeatedly fails
- the report output looks suspicious
- the user explicitly asks about internals

## Failure interpretations

### Bot challenge
Typical message:
- `Sign in to confirm you’re not a bot`

Meaning:
- YouTube is blocking the fetch path.

Best next move:
- reuse cached local copy if one exists
- otherwise check residential proxy / cookies

### 403 on media download
Typical message:
- `HTTP Error 403: Forbidden`

Meaning:
- Often caused by repeated reruns, expiring media URLs, or extractor restrictions.

Best next move:
- prefer the cached local copy
- avoid repeated fresh URL downloads for focused windows

### Missing transcript
Meaning:
- no captions found and transcription fallback unavailable or disabled

Best next move:
- run `python3 scripts/setup.py`
- add `OPENAI_API_KEY`
- re-run without `--no-transcribe`

## Preflight JSON fields

```bash
python3 scripts/setup.py --json
```

Useful fields now include:
- `has_proxy`
- `js_runtimes`
- `cookies_available`

Use these to decide whether a YouTube retry is likely to work before you keep poking at it.
