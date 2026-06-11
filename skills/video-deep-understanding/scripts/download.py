#!/usr/bin/env python3
"""Download a video via yt-dlp, or resolve a local file path.

Also fetches subtitles (manual first, then auto-generated) in VTT format so
transcribe.py can parse them without needing Whisper.

Uses a residential proxy (REDDIT_PROXY_URL) when available to bypass YouTube
bot detection, loading credentials via the shared credential hierarchy.

Successful URL downloads are cached in the system temp directory so focused
follow-up runs can reuse the local file instead of re-downloading the source.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

# Load shared credential helper (env var → ~/.bashrc fallback)
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'shared'))
from credentials import load_credential  # type: ignore


VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".flv", ".wmv"}
CACHE_ROOT = Path(tempfile.gettempdir()) / "video-deep-understanding-cache"
CACHE_INDEX_PATH = CACHE_ROOT / "index.json"


def is_url(source: str) -> bool:
    parsed = urlparse(source)
    return parsed.scheme in ("http", "https")


def resolve_local(path: str) -> dict:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise SystemExit(f"File not found: {p}")
    if p.suffix.lower() not in VIDEO_EXTS:
        print(
            f"[vdu] warning: {p.suffix} is not a known video extension, proceeding anyway",
            file=sys.stderr,
        )
    # Discover subtitle files next to the video (same basename, .vtt/.srt)
    subtitle: str | None = None
    for ext in (".vtt", ".en.vtt", ".srt", ".en.srt"):
        candidate = p.with_suffix(ext)
        if candidate.exists():
            subtitle = str(candidate)
            break
    return {
        "video_path": str(p),
        "subtitle_path": subtitle,
        "info": {"title": p.name, "url": str(p)},
        "downloaded": False,
        "cache_hit": False,
    }


def _pick_subtitle(out_dir: Path) -> Path | None:
    candidates = sorted(out_dir.glob("video*.vtt"))
    if not candidates:
        return None
    preferred = [c for c in candidates if ".en" in c.name]
    return preferred[0] if preferred else candidates[0]


def _pick_video(out_dir: Path) -> Path | None:
    for ext in (".mp4", ".mkv", ".webm", ".mov"):
        for candidate in out_dir.glob(f"video*{ext}"):
            return candidate
    for candidate in out_dir.glob("video.*"):
        if candidate.suffix.lower() in VIDEO_EXTS:
            return candidate
    return None


def _get_proxy_url() -> str | None:
    """Load residential proxy URL via shared credential loader."""
    try:
        return load_credential('VIDEO_PROXY_URL', required=False) or load_credential('REDDIT_PROXY_URL', required=False)  # type: ignore
    except Exception:
        return None


def _read_cache_index() -> dict[str, dict]:
    try:
        return json.loads(CACHE_INDEX_PATH.read_text())
    except Exception:
        return {}


def _write_cache_index(index: dict[str, dict]) -> None:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    CACHE_INDEX_PATH.write_text(json.dumps(index, indent=2))


def get_cached_download(url: str) -> dict | None:
    entry = _read_cache_index().get(url)
    if not entry:
        return None

    video_path = entry.get("video_path")
    subtitle_path = entry.get("subtitle_path")
    if not video_path or not Path(video_path).exists():
        return None
    if subtitle_path and not Path(subtitle_path).exists():
        subtitle_path = None

    info = entry.get("info") or {"url": url}
    return {
        "video_path": str(Path(video_path).resolve()),
        "subtitle_path": str(Path(subtitle_path).resolve()) if subtitle_path else None,
        "info": info,
        "downloaded": False,
        "cache_hit": True,
    }


def update_cached_download(url: str, payload: dict) -> None:
    index = _read_cache_index()
    index[url] = {
        "video_path": payload["video_path"],
        "subtitle_path": payload.get("subtitle_path"),
        "info": payload.get("info") or {"url": url},
    }
    _write_cache_index(index)


def classify_yt_dlp_failure(log_text: str) -> str:
    lower = log_text.lower()
    if "sign in to confirm you’re not a bot" in lower or "sign in to confirm you're not a bot" in lower:
        return (
            "yt-dlp hit a YouTube bot challenge. Reuse a previously cached local copy if available, "
            "or configure cookies / a residential proxy before retrying."
        )
    if "http error 403" in lower or "forbidden" in lower:
        return (
            "yt-dlp was denied the media download (HTTP 403). This often happens on repeated YouTube reruns; "
            "prefer a cached local copy, or retry with cookies / proxy support."
        )
    if "no supported javascript runtime" in lower:
        return (
            "yt-dlp could not find a supported JavaScript runtime. Install node, bun, or deno to improve "
            "YouTube extraction reliability."
        )
    if "cookies" in lower and "browser" in lower:
        return "yt-dlp appears to need browser cookies for this source. Export cookies or use --cookies-from-browser."
    return "yt-dlp failed before producing a local video file. Review the stderr above for source-specific details."


def _emit_process_output(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        print(result.stdout, file=sys.stderr, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")


def download_url(url: str, out_dir: Path) -> dict:
    if shutil.which("yt-dlp") is None:
        raise SystemExit("yt-dlp is not installed. Install with: brew install yt-dlp")

    cached = get_cached_download(url)
    if cached is not None:
        print(f"[vdu] reusing cached local download for {url}", file=sys.stderr)
        return cached

    out_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(out_dir / "video.%(ext)s")

    cmd = [
        "yt-dlp",
        "-N", "8",
        "-f", "bv*[height<=720]+ba/b[height<=720]/bv+ba/b",
        "--merge-output-format", "mp4",
        "--write-info-json",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", "en,en-US,en-GB,en-orig",
        "--sub-format", "vtt",
        "--convert-subs", "vtt",
        "--no-playlist",
        "--ignore-errors",
        "-o", output_template,
        url,
    ]

    env = dict(subprocess.os.environ)
    proxy_url = _get_proxy_url()
    if proxy_url:
        cmd.insert(1, "--proxy")
        cmd.insert(2, proxy_url)
        env["HTTP_PROXY"] = proxy_url
        env["HTTPS_PROXY"] = proxy_url
        print(f"[vdu] using residential proxy for download", file=sys.stderr)

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    _emit_process_output(result)

    video = _pick_video(out_dir)
    if video is None:
        combined_log = "\n".join(part for part in (result.stdout, result.stderr) if part)
        raise SystemExit(
            f"{classify_yt_dlp_failure(combined_log)} "
            f"(yt-dlp exit {result.returncode}; no video file in {out_dir})"
        )

    subtitle = _pick_subtitle(out_dir)
    info_path = out_dir / "video.info.json"
    info: dict = {}
    if info_path.exists():
        try:
            raw = json.loads(info_path.read_text())
            info = {
                "title": raw.get("title"),
                "uploader": raw.get("uploader") or raw.get("channel"),
                "duration": raw.get("duration"),
                "url": raw.get("webpage_url") or url,
            }
        except Exception:
            info = {"url": url}

    payload = {
        "video_path": str(video.resolve()),
        "subtitle_path": str(subtitle.resolve()) if subtitle else None,
        "info": info or {"url": url},
        "downloaded": True,
        "cache_hit": False,
    }
    update_cached_download(url, payload)
    return payload


def download(source: str, out_dir: Path) -> dict:
    if is_url(source):
        return download_url(source, out_dir)
    return resolve_local(source)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: download.py <url-or-path> <out-dir>", file=sys.stderr)
        raise SystemExit(2)
    result = download(sys.argv[1], Path(sys.argv[2]))
    print(json.dumps(result, indent=2))
