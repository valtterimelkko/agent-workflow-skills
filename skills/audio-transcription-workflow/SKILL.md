---
name: audio-transcription-workflow
description: "Transcribe local audio files or voice notes into markdown files using the legacy VoiceNote Bot workflow: local Whisper primary, OpenAI transcription fallback, and OpenRouter GPT-5 nano cleanup. Make sure to use this whenever the user wants audio files, voice recordings, dictations, interviews, or Telegram-style voice notes turned into markdown/text files without using Telegram, especially for batch folders or when they want the same cleanup behaviour as the old Telegram path."
version: 1.0.0
---

# Audio Transcription Workflow

Use this skill when the user wants to convert one or more local audio files into cleaned markdown transcripts using the same core workflow as a legacy voice-note transcription bot path, but without Telegram, webhooks, or queues.

## What this skill does

For each input audio file, the bundled script:
1. tries **local Whisper** first
2. falls back to **OpenAI transcription** (`gpt-4o-mini-transcribe` by default) if Whisper fails
3. runs **OpenRouter cleanup** with **`openai/gpt-5-nano`** unless cleanup is explicitly skipped or the API key is unavailable
4. writes a **markdown file** with a YAML metadata header and the cleaned transcript body
5. writes a `transcription_manifest.json` summary into the output directory

## Prefer this skill over simpler transcription paths when

Use this skill instead of a basic one-shot transcription skill when the user wants any of the following:
- the **same workflow as the old VoiceNote Bot**
- **markdown output files**, not just inline text
- **batch transcription** of many files or a folder
- **cleanup/editing** after raw STT
- **voice notes placed on disk** rather than sent through Telegram

## Inputs this skill accepts

- a single audio file
- multiple audio files
- a folder containing audio files
- a glob such as `/path/to/*.m4a`
- recursive folder traversal with `--recursive`

Supported formats:
- `.oga`, `.ogg`, `.mp3`, `.m4a`, `.wav`, `.webm`, `.mp4`, `.mpeg`, `.mpga`

## Output format

Each transcript is saved as a `.md` file with a metadata header like this:

```yaml
---
source_file: "note-01.oga"
source_path: "/absolute/path/note-01.oga"
generated_at: "2026-05-28T10:00:00+00:00"
workflow: "local_whisper_primary_openai_fallback_openrouter_cleanup"
language_requested: "auto"
transcription_provider: "whisper"
transcription_model: "local-whisper"
cleanup_applied: true
cleanup_provider: "openrouter"
cleanup_model: "openai/gpt-5-nano"
warnings: []
---
```

The markdown body below the header is the transcript the user should read or reuse.

## Bundled script

Use this script:

```bash
python3 ./skills/audio-transcription-workflow/scripts/transcribe_audio_to_markdown.py ...
```

## Common commands

### Single file

```bash
python3 ./skills/audio-transcription-workflow/scripts/transcribe_audio_to_markdown.py \
  /path/to/voice-note.oga \
  --output-dir /path/to/output
```

### Multiple files

```bash
python3 ./skills/audio-transcription-workflow/scripts/transcribe_audio_to_markdown.py \
  /path/to/a.oga /path/to/b.m4a /path/to/c.wav \
  --output-dir /path/to/output
```

### Folder

```bash
python3 ./skills/audio-transcription-workflow/scripts/transcribe_audio_to_markdown.py \
  /path/to/audio-folder \
  --output-dir /path/to/output
```

### Recursive folder

```bash
python3 ./skills/audio-transcription-workflow/scripts/transcribe_audio_to_markdown.py \
  /path/to/audio-folder \
  --recursive \
  --output-dir /path/to/output
```

### Glob input

```bash
python3 ./skills/audio-transcription-workflow/scripts/transcribe_audio_to_markdown.py \
  '/path/to/audio/*.m4a' \
  --output-dir /path/to/output
```

### Raw transcript only

If the user explicitly wants no cleanup:

```bash
python3 ./skills/audio-transcription-workflow/scripts/transcribe_audio_to_markdown.py \
  /path/to/audio-folder \
  --output-dir /path/to/output \
  --skip-cleanup
```

## Environment requirements

Expected environment variables:
- `WHISPER_URL` — optional, defaults to `http://localhost:9000/asr`
- `OPENAI_API_KEY` — optional but needed for transcription fallback
- `OPENAI_TRANSCRIPTION_MODEL` — optional, defaults to `gpt-4o-mini-transcribe`
- `OPENROUTER_API_KEY` — optional but needed for legacy-style cleanup

The bundled script tries to work for low-context agents too.
- Credentials such as `OPENROUTER_API_KEY` and `OPENAI_API_KEY` are resolved in this order: current process environment → a shell startup file such as `~/.bashrc` via the shared credential loader → an optional legacy dotenv file pointed to by `AUDIO_TRANSCRIPTION_LEGACY_ENV` if you deliberately enable that fallback.
- `WHISPER_URL` stays simple: current process environment first, otherwise the script uses its built-in localhost default.

That means cleanup should usually work even when an agent has not been explicitly told where the OpenRouter key lives.

## How to operate the skill

1. Resolve the user's input path(s).
2. Decide on an output directory.
   - Prefer a user-specified output directory.
   - Otherwise use a sensible local folder such as `./transcriptions` near the current task context.
3. Run the bundled script.
4. Read the generated `.md` files if you need to summarise results back to the user.
5. Mention:
   - where the markdown transcripts were saved
   - whether any file used the OpenAI fallback
   - whether cleanup was skipped or failed for any file
   - where `transcription_manifest.json` was saved

## Behaviour notes

- The script serialises Whisper access with a local file lock to avoid CPU-heavy concurrent Whisper requests.
- If Whisper fails and `OPENAI_API_KEY` is missing, that file fails.
- If OpenRouter cleanup fails or no OpenRouter key can be resolved from the environment / shell startup file / optional legacy dotenv fallback, the script still writes markdown using the raw transcript and records a warning in metadata and in the manifest.
- `WHISPER_URL` is intentionally not pulled from any legacy dotenv fallback, because those files may contain hostnames that are wrong for direct host-side agent use.
- Output file collisions are handled automatically by appending `-2`, `-3`, and so on.

## Good response pattern

After running the script, give a short operational summary such as:
- how many files were processed
- how many succeeded or failed
- output directory path
- whether cleanup matched the legacy path fully or had fallbacks/skips

## Example user requests that should trigger this skill

- "Take these voice notes in `/path/to/meeting-notes/` and turn them into markdown transcripts."
- "Use the old Telegram transcription workflow on these `.oga` files, but without Telegram."
- "Batch transcribe all my interview `.m4a` files into markdown with cleanup."
- "I dropped three audio files in Downloads — convert them into transcript markdown files." 
