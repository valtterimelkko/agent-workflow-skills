#!/usr/bin/env python3
"""Transcribe audio files to markdown using the legacy VoiceNote Bot workflow.

Workflow:
- local Whisper primary
- OpenAI audio transcription fallback
- OpenRouter GPT-5 nano cleanup
- markdown output with YAML metadata header
"""

from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

SUPPORTED_EXTENSIONS = {".oga", ".ogg", ".mp3", ".m4a", ".wav", ".webm", ".mp4", ".mpeg", ".mpga"}
WHISPER_SUPPORTED_EXTENSIONS = {".oga", ".ogg", ".mp3", ".m4a", ".wav", ".webm"}
OPENAI_SUPPORTED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}
DEFAULT_CLEANUP_MODEL = "openai/gpt-5-nano"
DEFAULT_WHISPER_URL_FALLBACK = "http://localhost:9000/asr"
DEFAULT_OPENAI_MODEL_FALLBACK = "gpt-4o-mini-transcribe"
WORKFLOW_NAME = "local_whisper_primary_openai_fallback_openrouter_cleanup"
LOCK_PATH = "/tmp/audio-transcription-workflow.whisper.lock"
LEGACY_ENV_PATH = os.getenv("AUDIO_TRANSCRIPTION_LEGACY_ENV")
VOICEBOT_ENV_PATH = Path(LEGACY_ENV_PATH) if LEGACY_ENV_PATH else None
SHARED_CREDENTIALS_PATH = Path(__file__).resolve().parents[3] / "shared" / "credentials.py"


def _parse_dotenv_value(env_path: Path | None, key: str) -> str | None:
    if env_path is None or not env_path.exists():
        return None
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            if not line.startswith(f"{key}="):
                continue
            value = line.split("=", 1)[1].strip().strip('"\'')
            if " #" in value:
                value = value.split(" #", 1)[0].strip()
            return value or None
    except Exception:
        return None
    return None


def _load_shared_credential(key: str) -> str | None:
    if not SHARED_CREDENTIALS_PATH.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("skills_global_credentials", SHARED_CREDENTIALS_PATH)
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        value = module.load_credential(key, required=False)
        return value or None
    except Exception:
        return None


def hydrate_env_var(
    key: str,
    default: str | None = None,
    *,
    allow_bashrc: bool = True,
    allow_voicebot_dotenv: bool = True,
) -> str | None:
    value = os.getenv(key)
    if value:
        return value

    if allow_bashrc:
        value = _load_shared_credential(key)
        if value:
            os.environ[key] = value
            return value

    if allow_voicebot_dotenv:
        value = _parse_dotenv_value(VOICEBOT_ENV_PATH, key)
        if value:
            os.environ[key] = value
            return value

    if default is not None and not os.getenv(key):
        os.environ[key] = default
        return default

    return None


def bootstrap_runtime_environment() -> None:
    hydrate_env_var("OPENROUTER_API_KEY")
    hydrate_env_var("OPENAI_API_KEY")
    hydrate_env_var("OPENAI_TRANSCRIPTION_MODEL", DEFAULT_OPENAI_MODEL_FALLBACK)
    hydrate_env_var("WHISPER_URL", DEFAULT_WHISPER_URL_FALLBACK, allow_bashrc=False, allow_voicebot_dotenv=False)


bootstrap_runtime_environment()

DEFAULT_WHISPER_URL = os.getenv("WHISPER_URL", DEFAULT_WHISPER_URL_FALLBACK)
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", DEFAULT_OPENAI_MODEL_FALLBACK)


class TranscriptionWorkflowError(Exception):
    """Base workflow error."""


class WhisperError(TranscriptionWorkflowError):
    """Raised when local Whisper transcription fails."""


class OpenAITranscriptionError(TranscriptionWorkflowError):
    """Raised when OpenAI fallback transcription fails."""


class OpenRouterCleanupError(TranscriptionWorkflowError):
    """Raised when OpenRouter cleanup fails."""


@contextmanager
def whisper_lock() -> Any:
    """Serialize Whisper access to avoid CPU contention."""
    Path(LOCK_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_PATH, "w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def looks_like_glob(path_str: str) -> bool:
    return any(ch in path_str for ch in "*?[]")


def unique_output_path(output_dir: Path, stem: str) -> Path:
    candidate = output_dir / f"{stem}.md"
    counter = 2
    while candidate.exists():
        candidate = output_dir / f"{stem}-{counter}.md"
        counter += 1
    return candidate


def safe_stem(path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", path.stem).strip("-._")
    return stem or "transcript"


def collect_input_files(inputs: list[str], recursive: bool) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    for raw_input in inputs:
        matches: list[Path] = []
        if looks_like_glob(raw_input):
            import glob
            matches = [Path(p) for p in glob.glob(raw_input, recursive=recursive)]
        else:
            matches = [Path(raw_input)]

        if not matches:
            raise FileNotFoundError(f"No files matched input: {raw_input}")

        for match in matches:
            if not match.exists():
                raise FileNotFoundError(f"Input not found: {match}")
            if match.is_dir():
                pattern = "**/*" if recursive else "*"
                for child in match.glob(pattern):
                    if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
                        resolved = child.resolve()
                        if resolved not in seen:
                            seen.add(resolved)
                            files.append(resolved)
            else:
                resolved = match.resolve()
                if resolved.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    raise ValueError(f"Unsupported audio format: {resolved}")
                if resolved not in seen:
                    seen.add(resolved)
                    files.append(resolved)

    if not files:
        raise FileNotFoundError("No supported audio files found")

    return sorted(files)


def whisper_mime_type(audio_path: Path) -> str:
    file_ext = audio_path.suffix.lower()
    mime_types = {
        ".oga": "audio/ogg",
        ".ogg": "audio/ogg",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".wav": "audio/wav",
        ".webm": "audio/webm",
    }
    return mime_types.get(file_ext, mimetypes.guess_type(audio_path.name)[0] or "audio/ogg")


def transcribe_with_whisper(audio_path: Path, whisper_url: str, language: str) -> str:
    with whisper_lock():
        with audio_path.open("rb") as audio_file:
            file_content = audio_file.read()

        files = {"audio_file": (audio_path.name, file_content, whisper_mime_type(audio_path))}
        data = {"language": language}

        try:
            response = httpx.post(
                whisper_url,
                files=files,
                data=data,
                timeout=300.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise WhisperError(f"Whisper HTTP {exc.response.status_code}: {exc.response.text[:300]}") from exc
        except httpx.TimeoutException as exc:
            raise WhisperError("Whisper request timed out") from exc
        except Exception as exc:
            raise WhisperError(f"Whisper request failed: {exc}") from exc

    transcript = response.text.strip()
    if not transcript:
        raise WhisperError("Whisper returned an empty transcript")
    return transcript


class OpenAITranscriber:
    def __init__(self, api_key: str, model: str = DEFAULT_OPENAI_MODEL):
        self.api_key = api_key
        self.model = model
        self.client = httpx.Client(
            timeout=httpx.Timeout(120.0, connect=30.0),
            follow_redirects=True,
        )

    def close(self) -> None:
        self.client.close()

    def _convert_to_supported_audio(self, audio_path: Path) -> tuple[Path, bool]:
        if audio_path.suffix.lower() in OPENAI_SUPPORTED_EXTENSIONS:
            return audio_path, False

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_path = Path(tmp.name)

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(audio_path),
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-c:a",
                    "pcm_s16le",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            return output_path, True
        except subprocess.CalledProcessError as exc:
            if output_path.exists():
                output_path.unlink(missing_ok=True)
            raise OpenAITranscriptionError(f"ffmpeg conversion failed: {exc.stderr}") from exc
        except FileNotFoundError as exc:
            if output_path.exists():
                output_path.unlink(missing_ok=True)
            raise OpenAITranscriptionError("ffmpeg not found for OpenAI fallback conversion") from exc

    def transcribe(self, audio_path: Path, language: str) -> str:
        upload_path, created_temp = self._convert_to_supported_audio(audio_path)
        try:
            with upload_path.open("rb") as audio_file:
                files = {
                    "file": (
                        upload_path.name,
                        audio_file,
                        mimetypes.guess_type(upload_path.name)[0] or "audio/wav",
                    )
                }
                data: dict[str, str] = {
                    "model": self.model,
                    "response_format": "json",
                }
                if language and language != "auto":
                    data["language"] = language

                response = self.client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files,
                    data=data,
                )
                response.raise_for_status()

            payload = response.json()
            transcript = (payload.get("text") or "").strip()
            if not transcript:
                raise OpenAITranscriptionError("OpenAI fallback returned an empty transcript")
            return transcript
        except httpx.HTTPStatusError as exc:
            raise OpenAITranscriptionError(
                f"OpenAI HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise OpenAITranscriptionError("OpenAI transcription request timed out") from exc
        except Exception as exc:
            if isinstance(exc, OpenAITranscriptionError):
                raise
            raise OpenAITranscriptionError(f"OpenAI transcription request failed: {exc}") from exc
        finally:
            if created_temp:
                upload_path.unlink(missing_ok=True)


class OpenRouterCleaner:
    SYSTEM_PROMPT = (
        "You are a transcription editor. Clean up voice transcripts with a LIGHT touch:\n"
        "1. Fix spelling and grammar mistakes only when they're clearly wrong\n"
        "2. Convert American spellings to British (color→colour, organize→organise, etc.)\n"
        "3. Remove filler words (um, uh, mmm, ooh, aah, öö, ääh, etc.)\n"
        "4. Fix obvious transcription errors\n"
        "5. Preserve the original language (don't translate)\n"
        "6. IMPORTANT: Keep the speaker's authentic voice, quirks, and natural speech patterns\n"
        "   - Do NOT remove sentences or restructure the flow\n"
        "   - Do NOT replace words just to make it sound more 'proper' or 'perfect'\n"
        "   - Do NOT smooth out rough edges or back-and-forth thinking\n"
        "   - Preserve non-native speaker expressions and authentic word choices\n"
        "   - Keep fragmented sentences if that's how the person speaks\n"
        "   - The transcript will be used for prompting LLMs, not for publication\n\n"
        "Return ONLY the cleaned text, nothing else."
    )

    def __init__(self, api_key: str, model: str = DEFAULT_CLEANUP_MODEL):
        self.api_key = api_key
        self.model = model
        self.client = httpx.Client(
            timeout=httpx.Timeout(300.0, connect=30.0),
            follow_redirects=True,
        )

    def close(self) -> None:
        self.client.close()

    def cleanup(self, transcript_text: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Clean up this transcript:\n\n{transcript_text}"},
            ],
            "temperature": 0.3,
            "max_tokens": 60000,
        }

        try:
            response = self.client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://audio-transcription-workflow.local",
                    "X-Title": "Audio Transcription Workflow",
                },
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise OpenRouterCleanupError(
                f"OpenRouter HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise OpenRouterCleanupError("OpenRouter cleanup request timed out") from exc
        except Exception as exc:
            raise OpenRouterCleanupError(f"OpenRouter cleanup request failed: {exc}") from exc

        try:
            data = response.json()
            cleaned = data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise OpenRouterCleanupError(f"Unexpected OpenRouter response: {exc}") from exc

        if not cleaned:
            raise OpenRouterCleanupError("OpenRouter returned an empty cleanup result")
        return cleaned


def build_markdown(
    source_path: Path,
    cleaned_text: str,
    transcription_provider: str,
    transcription_model: str,
    cleanup_applied: bool,
    cleanup_provider: str | None,
    cleanup_model: str | None,
    warnings: list[str],
    language: str,
) -> str:
    metadata_lines = [
        "---",
        f"source_file: {yaml_quote(source_path.name)}",
        f"source_path: {yaml_quote(str(source_path))}",
        f"generated_at: {yaml_quote(now_iso())}",
        f"workflow: {yaml_quote(WORKFLOW_NAME)}",
        f"language_requested: {yaml_quote(language)}",
        f"transcription_provider: {yaml_quote(transcription_provider)}",
        f"transcription_model: {yaml_quote(transcription_model)}",
        f"cleanup_applied: {'true' if cleanup_applied else 'false'}",
        f"cleanup_provider: {yaml_quote(cleanup_provider) if cleanup_provider else 'null'}",
        f"cleanup_model: {yaml_quote(cleanup_model) if cleanup_model else 'null'}",
    ]
    if warnings:
        metadata_lines.append("warnings:")
        metadata_lines.extend(f"  - {yaml_quote(item)}" for item in warnings)
    else:
        metadata_lines.append("warnings: []")
    metadata_lines.extend([
        "---",
        "",
        f"# {source_path.stem}",
        "",
        cleaned_text.strip(),
        "",
    ])
    return "\n".join(metadata_lines)


def transcribe_one(
    audio_path: Path,
    whisper_url: str,
    language: str,
    openai_api_key: str | None,
    openai_model: str,
    openrouter_api_key: str | None,
    skip_cleanup: bool,
    output_dir: Path,
) -> dict[str, Any]:
    warnings: list[str] = []
    raw_transcript: str
    transcription_provider: str
    transcription_model: str

    try:
        raw_transcript = transcribe_with_whisper(audio_path, whisper_url, language)
        transcription_provider = "whisper"
        transcription_model = "local-whisper"
    except WhisperError as whisper_exc:
        warnings.append(f"Whisper failed: {whisper_exc}")
        if not openai_api_key:
            raise TranscriptionWorkflowError(
                f"Whisper failed and OPENAI_API_KEY is not set for fallback: {whisper_exc}"
            ) from whisper_exc
        openai_transcriber = OpenAITranscriber(api_key=openai_api_key, model=openai_model)
        try:
            raw_transcript = openai_transcriber.transcribe(audio_path, language)
            transcription_provider = "openai"
            transcription_model = openai_model
        finally:
            openai_transcriber.close()

    cleaned_text = raw_transcript
    cleanup_applied = False
    cleanup_provider: str | None = None
    cleanup_model: str | None = None

    if skip_cleanup:
        warnings.append("Cleanup skipped by --skip-cleanup")
    elif not openrouter_api_key:
        warnings.append("OPENROUTER_API_KEY not set; using raw transcript without cleanup")
    else:
        cleaner = OpenRouterCleaner(api_key=openrouter_api_key, model=DEFAULT_CLEANUP_MODEL)
        try:
            cleaned_text = cleaner.cleanup(raw_transcript)
            cleanup_applied = True
            cleanup_provider = "openrouter"
            cleanup_model = DEFAULT_CLEANUP_MODEL
        except OpenRouterCleanupError as cleanup_exc:
            warnings.append(f"Cleanup failed; using raw transcript: {cleanup_exc}")
        finally:
            cleaner.close()

    output_path = unique_output_path(output_dir, safe_stem(audio_path))
    markdown = build_markdown(
        source_path=audio_path,
        cleaned_text=cleaned_text,
        transcription_provider=transcription_provider,
        transcription_model=transcription_model,
        cleanup_applied=cleanup_applied,
        cleanup_provider=cleanup_provider,
        cleanup_model=cleanup_model,
        warnings=warnings,
        language=language,
    )
    output_path.write_text(markdown, encoding="utf-8")

    return {
        "source": str(audio_path),
        "output": str(output_path),
        "transcription_provider": transcription_provider,
        "transcription_model": transcription_model,
        "cleanup_applied": cleanup_applied,
        "cleanup_provider": cleanup_provider,
        "cleanup_model": cleanup_model,
        "warnings": warnings,
        "success": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe audio files to markdown using local Whisper, OpenAI fallback, and OpenRouter cleanup."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Audio file(s), folder(s), or glob(s) to transcribe",
    )
    parser.add_argument(
        "--output-dir",
        default="./transcriptions",
        help="Directory where markdown transcripts will be written (default: ./transcriptions)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recurse into subfolders when an input is a directory or recursive glob",
    )
    parser.add_argument(
        "--language",
        default="auto",
        help="Language hint for transcription (default: auto)",
    )
    parser.add_argument(
        "--whisper-url",
        default=DEFAULT_WHISPER_URL,
        help=f"Whisper ASR endpoint (default: {DEFAULT_WHISPER_URL})",
    )
    parser.add_argument(
        "--openai-model",
        default=DEFAULT_OPENAI_MODEL,
        help=f"OpenAI fallback transcription model (default: {DEFAULT_OPENAI_MODEL})",
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Skip OpenRouter cleanup and write raw transcript text to markdown",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        input_files = collect_input_files(args.inputs, recursive=args.recursive)
    except Exception as exc:
        print(f"Error collecting input files: {exc}", file=sys.stderr)
        return 2

    openai_api_key = os.getenv("OPENAI_API_KEY") or None
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY") or None

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for audio_path in input_files:
        try:
            result = transcribe_one(
                audio_path=audio_path,
                whisper_url=args.whisper_url,
                language=args.language,
                openai_api_key=openai_api_key,
                openai_model=args.openai_model,
                openrouter_api_key=openrouter_api_key,
                skip_cleanup=args.skip_cleanup,
                output_dir=output_dir,
            )
            results.append(result)
            print(f"✓ {audio_path} -> {result['output']}")
        except Exception as exc:
            failure = {
                "source": str(audio_path),
                "success": False,
                "error": str(exc),
            }
            failures.append(failure)
            print(f"✗ {audio_path} -> {exc}", file=sys.stderr)

    manifest = {
        "generated_at": now_iso(),
        "workflow": WORKFLOW_NAME,
        "output_dir": str(output_dir),
        "total_inputs": len(input_files),
        "successful": len(results),
        "failed": len(failures),
        "results": results,
        "failures": failures,
    }
    manifest_path = output_dir / "transcription_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Manifest written to {manifest_path}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
