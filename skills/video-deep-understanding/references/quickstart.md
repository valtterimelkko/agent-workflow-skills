# Video Deep Understanding — Quickstart

Use this skill in three passes when the task allows it:

1. **Preflight**
   ```bash
   python3 scripts/setup.py --check
   ```
   Stay silent on success.

2. **Transcript-first narrowing** for long videos or concept-finding tasks
   ```bash
   python3 scripts/watch.py "$URL" --transcript-only --find 'kanban|retry|handoff'
   ```
   This avoids paying image-token cost before you know where to zoom in.

3. **Focused visual pass** on the relevant window
   ```bash
   python3 scripts/watch.py "$URL" --start 4:32 --end 5:16 --resolution 1024 --contact-sheet
   ```

## Useful flags

- `--transcript-only` — skip frame extraction entirely
- `--find REGEX` — show transcript matches and suggested focus windows
- `--compact-report` — shorter report for agent workflows
- `--contact-sheet` — best-effort composite image of extracted frames
- `--start` / `--end` — focus on a specific time range
- `--resolution 1024` — better for reading on-screen UI text

## Cache reuse

Successful URL downloads are cached automatically in the system temp directory.
If you re-run the same URL later, the downloader will prefer the cached local copy instead of hitting YouTube again.
This is especially important after a first successful download: follow-up focused passes should usually reuse the local cache.

## Recommended decision rule

- **Short video + broad summary** → full scan is fine.
- **Long video (>10 min)** → transcript-first, then focused visual windows.
- **UI/demo/tutorial** → use `--resolution 1024`, often with `--contact-sheet`.
- **User asks about one named concept** → use `--find` first.
