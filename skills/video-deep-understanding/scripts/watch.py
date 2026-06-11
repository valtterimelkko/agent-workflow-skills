#!/usr/bin/env python3
"""Entry point: download video, extract frames, parse transcript.

Prints a markdown report to stdout listing frame paths + transcript. The agent
then reads each frame path to see the video.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from download import download, is_url  # noqa: E402
from frames import MAX_FPS, auto_fps, auto_fps_focus, extract, format_time, get_metadata, parse_time  # noqa: E402
from transcribe import filter_range, format_transcript, parse_vtt  # noqa: E402
from whisper import load_api_key, transcribe_video  # noqa: E402


def _build_match_summary(segments: list[dict], pattern: str) -> tuple[list[dict], list[tuple[float, float]]]:
    rx = re.compile(pattern, re.IGNORECASE)
    matches = [seg for seg in segments if rx.search(seg.get("text", ""))]
    windows: list[tuple[float, float]] = []
    for seg in matches:
        start = max(0.0, seg["start"] - 15.0)
        end = seg["end"] + 15.0
        if windows and start <= windows[-1][1]:
            windows[-1] = (windows[-1][0], max(windows[-1][1], end))
        else:
            windows.append((start, end))
    return matches, windows


def _create_contact_sheet(frame_paths: list[str], out_path: Path, columns: int = 3) -> str | None:
    if not frame_paths:
        return None
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None

    thumbs = []
    for frame_path in frame_paths:
        img = Image.open(frame_path).convert("RGB")
        width = min(360, img.size[0])
        height = max(1, int(img.size[1] * (width / img.size[0])))
        thumb = img.resize((width, height))
        draw = ImageDraw.Draw(thumb)
        label = Path(frame_path).stem.replace("frame_", "")
        draw.rectangle((0, 0, min(200, width), 22), fill=(0, 0, 0))
        draw.text((6, 4), label, fill=(255, 255, 255))
        thumbs.append(thumb)

    rows = (len(thumbs) + columns - 1) // columns
    cell_w = max(t.size[0] for t in thumbs)
    cell_h = max(t.size[1] for t in thumbs)
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), (255, 255, 255))
    for i, thumb in enumerate(thumbs):
        x = (i % columns) * cell_w
        y = (i // columns) * cell_h
        sheet.paste(thumb, (x, y))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=90)
    return str(out_path)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="video-deep-understanding",
        description="Download a video, extract auto-scaled frames, and surface the transcript.",
    )
    ap.add_argument("source", help="Video URL or local file path")
    ap.add_argument("--max-frames", type=int, default=80, help="Cap on frame count (default 80, hard max 100)")
    ap.add_argument("--resolution", type=int, default=512, help="Frame width in pixels (default 512)")
    ap.add_argument("--fps", type=float, default=None, help="Override auto-fps")
    ap.add_argument("--start", type=str, default=None, help="Range start (SS, MM:SS, or HH:MM:SS)")
    ap.add_argument("--end", type=str, default=None, help="Range end (SS, MM:SS, or HH:MM:SS)")
    ap.add_argument("--out-dir", type=str, default=None, help="Working directory (default: tmp)")
    ap.add_argument("--transcript-only", action="store_true", help="Skip frame extraction and return transcript only")
    ap.add_argument("--find", type=str, default=None, help="Regex/keyword pattern to find in the transcript")
    ap.add_argument("--compact-report", action="store_true", help="Emit a shorter report for agent workflows")
    ap.add_argument("--contact-sheet", action="store_true", help="Generate a contact sheet image when frames are extracted")
    ap.add_argument(
        "--no-transcribe",
        action="store_true",
        help="Disable transcription fallback. Report frames-only if no captions available.",
    )
    args = ap.parse_args()

    max_frames = min(args.max_frames, 100)

    if args.out_dir:
        work = Path(args.out_dir).expanduser().resolve()
    else:
        work = Path(tempfile.mkdtemp(prefix="vdu-"))
    work.mkdir(parents=True, exist_ok=True)
    print(f"[vdu] working dir: {work}", file=sys.stderr)

    print(
        "[vdu] downloading via yt-dlp…" if is_url(args.source) else "[vdu] using local file…",
        file=sys.stderr,
    )
    dl = download(args.source, work / "download")
    video_path = dl["video_path"]

    meta = get_metadata(video_path)
    full_duration = meta["duration_seconds"]

    start_sec = parse_time(args.start)
    end_sec = parse_time(args.end)

    if start_sec is not None and start_sec < 0:
        raise SystemExit("--start must be non-negative")
    if end_sec is not None and start_sec is not None and end_sec <= start_sec:
        raise SystemExit("--end must be greater than --start")
    if full_duration > 0 and start_sec is not None and start_sec >= full_duration:
        raise SystemExit(f"--start {start_sec:.1f}s is past end of video ({full_duration:.1f}s)")

    effective_start = start_sec if start_sec is not None else 0.0
    effective_end = end_sec if end_sec is not None else full_duration
    effective_duration = max(0.0, effective_end - effective_start)
    focused = start_sec is not None or end_sec is not None

    if focused:
        fps, target = auto_fps_focus(effective_duration, max_frames=max_frames)
    else:
        fps, target = auto_fps(effective_duration, max_frames=max_frames)
    if args.fps is not None:
        fps = min(args.fps, MAX_FPS)
        target = max(1, int(round(fps * effective_duration)))

    scope = (
        f"{format_time(effective_start)}-{format_time(effective_end)} ({effective_duration:.1f}s)"
        if focused else f"full {effective_duration:.1f}s"
    )

    frames: list[dict] = []
    contact_sheet_path: str | None = None
    mode = "transcript-only" if args.transcript_only else ("focused" if focused else "full")
    if not args.transcript_only:
        print(f"[vdu] extracting ~{target} frames at {fps:.3f} fps over {scope}…", file=sys.stderr)
        frames = extract(
            video_path,
            work / "frames",
            fps=fps,
            resolution=args.resolution,
            max_frames=max_frames,
            start_seconds=start_sec,
            end_seconds=end_sec,
        )
        if args.contact_sheet:
            contact_sheet_path = _create_contact_sheet(
                [frame["path"] for frame in frames],
                work / "frames" / "contact-sheet.jpg",
            )
            if contact_sheet_path:
                print(f"[vdu] contact sheet: {contact_sheet_path}", file=sys.stderr)
            else:
                print("[vdu] contact sheet skipped (Pillow unavailable or no frames)", file=sys.stderr)

    transcript_segments: list[dict] = []
    transcript_text: str | None = None
    transcript_source: str | None = None
    if dl.get("subtitle_path"):
        try:
            all_segments = parse_vtt(dl["subtitle_path"])
            transcript_segments = filter_range(all_segments, start_sec, end_sec) if focused else all_segments
            transcript_text = format_transcript(transcript_segments)
            transcript_source = "captions"
        except Exception as exc:
            print(f"[vdu] subtitle parse failed: {exc}", file=sys.stderr)

    if not transcript_segments and not args.no_transcribe:
        api_key = load_api_key()
        if api_key:
            try:
                all_segments = transcribe_video(
                    video_path,
                    work / "audio.mp3",
                    api_key=api_key,
                )
                if focused and all_segments and all(
                    s.get("start") == 0.0 and s.get("end") == 0.0 for s in all_segments
                ):
                    for s in all_segments:
                        s["start"] = effective_start
                        s["end"] = effective_end
                transcript_segments = filter_range(all_segments, start_sec, end_sec) if focused else all_segments
                transcript_text = format_transcript(transcript_segments)
                transcript_source = "openai (gpt-4o-transcribe)"
            except SystemExit as exc:
                print(f"[vdu] transcription fallback failed: {exc}", file=sys.stderr)
        else:
            setup_py = SCRIPT_DIR / "setup.py"
            print(
                f"[vdu] no subtitles and no OpenAI API key found — "
                f"run `python3 {setup_py}` to enable the transcription fallback",
                file=sys.stderr,
            )

    info = dl.get("info") or {}
    matches: list[dict] = []
    match_windows: list[tuple[float, float]] = []
    if transcript_segments and args.find:
        matches, match_windows = _build_match_summary(transcript_segments, args.find)

    print()
    print("# Video Deep Understanding Report")
    print()
    print(f"- **Source:** {args.source}")
    if info.get("title"):
        print(f"- **Title:** {info['title']}")
    if info.get("uploader"):
        print(f"- **Uploader:** {info['uploader']}")
    print(f"- **Mode:** {mode}")
    print(f"- **Duration:** {format_time(full_duration)} ({full_duration:.1f}s)")
    if dl.get("cache_hit"):
        print(f"- **Local cache reuse:** yes (`{video_path}`)")
    if focused:
        print(
            f"- **Focus range:** {format_time(effective_start)} → {format_time(effective_end)} "
            f"({effective_duration:.1f}s)"
        )
    if meta.get("width") and meta.get("height"):
        print(f"- **Resolution:** {meta['width']}x{meta['height']} ({meta.get('codec') or 'unknown codec'})")
    if not args.transcript_only:
        print(f"- **Frames:** {len(frames)} @ {fps:.3f} fps, {mode} mode (budget {target}, max {max_frames})")
        print(f"- **Frame size:** {args.resolution}px wide")
        if contact_sheet_path:
            print(f"- **Contact sheet:** `{contact_sheet_path}`")
    else:
        print("- **Frames:** skipped (`--transcript-only`)")
    if transcript_segments:
        in_range = " in range" if focused else ""
        print(
            f"- **Transcript:** {len(transcript_segments)} segments{in_range} "
            f"(via {transcript_source or 'captions'})"
        )
    else:
        print("- **Transcript:** none available")
    if args.find:
        print(f"- **Transcript search:** `{args.find}` → {len(matches)} match(es)")

    if not focused and full_duration > 600:
        mins = int(full_duration // 60)
        print()
        print(
            f"> **Warning:** This is a {mins}-minute video. Frame coverage is sparse at this length — "
            "accuracy degrades noticeably on anything over 10 minutes. For better results, "
            "prefer transcript-first narrowing (`--transcript-only --find 'keyword'`) and then "
            "re-run with `--start HH:MM:SS --end HH:MM:SS` on the relevant section."
        )

    if match_windows:
        print()
        print("## Transcript matches")
        print()
        for seg in matches:
            print(f"- `{format_time(seg['start'])}` — {seg['text']}")
        print()
        print("### Suggested focus windows")
        print()
        for start, end in match_windows:
            print(f"- `{format_time(start)} → {format_time(end)}`")

    if not args.compact_report:
        print()
        print("## Frames")
        print()
        if args.transcript_only:
            print("_Frame extraction skipped in transcript-only mode._")
        else:
            print(f"Frames live at: `{work / 'frames'}`")
            print()
            if contact_sheet_path:
                print(f"Contact sheet: `{contact_sheet_path}`")
                print()
            print(
                "**Read each frame path below with the Read tool to view the image.** "
                "Frames are in chronological order; `t=MM:SS` is the absolute timestamp in the source video."
            )
            print()
            for frame in frames:
                print(f"- `{frame['path']}` (t={format_time(frame['timestamp_seconds'])})")

    print()
    print("## Transcript")
    print()
    if transcript_text and not (args.compact_report and matches):
        label = transcript_source or "captions"
        if focused:
            print(f"_Source: {label}. Filtered to {format_time(effective_start)} → {format_time(effective_end)}:_")
        else:
            print(f"_Source: {label}._")
        print()
        print("```")
        print(transcript_text)
        print("```")
    elif transcript_text:
        print("_Transcript omitted in compact mode because match hits are listed above._")
    elif focused and dl.get("subtitle_path"):
        print(f"_No transcript lines fell inside {format_time(effective_start)} → {format_time(effective_end)}._")
    else:
        setup_py = SCRIPT_DIR / "setup.py"
        print(
            "_No transcript available — proceed with frames only. "
            "Captions were missing and the transcription fallback was unavailable "
            "(no API key set, or `--no-transcribe` was used). "
            f"Run `python3 {setup_py}` to enable transcription, then re-run._"
        )

    print()
    print("---")
    print(f"_Work dir: `{work}` — delete when done._")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
