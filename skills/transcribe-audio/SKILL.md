---
name: transcribe-audio
description: "Transcribe audio files to text using a local Whisper ASR service. Use when: the user wants to transcribe an audio file to text, convert speech to text from an audio recording, extract text from voice recordings, or needs transcription of podcasts/interviews/voice notes. Only works for English language audio. The skill saves the transcription to a text file in the agent's local folder."
---

# Transcribe Audio

Transcribe audio files to text using the local Whisper ASR service running at `http://localhost:9000`.

## Prerequisites

- The Whisper service must be running (check with `curl http://localhost:9000/health`)
- Audio file must be in a supported format: OGG, MP3, M4A, WAV, or WebM
- Audio must be in **English** (the local model is English-only)

## Usage

### Basic Transcription

To transcribe an audio file:

```bash
curl -X POST http://localhost:9000/asr \
  -F "audio_file=@/path/to/audio.wav" \
  -F "language=en"
```

### Save to File

Save the transcription to the agent's local folder:

```bash
curl -X POST http://localhost:9000/asr \
  -F "audio_file=@/path/to/audio.wav" \
  -F "language=en" \
  -o transcription.txt
```

Or with a specific output path:

```bash
OUTPUT_FILE="${PWD}/$(basename /path/to/audio.wav .wav).txt"
curl -X POST http://localhost:9000/asr \
  -F "audio_file=@/path/to/audio.wav" \
  -F "language=en" \
  -o "$OUTPUT_FILE"
```

## Quick Workflow

1. **Verify the service is running:**
   ```bash
   curl -s http://localhost:9000/health
   ```
   Expected response: `{"status": "ok"}`

2. **Transcribe and save:**
   ```bash
   curl -X POST http://localhost:9000/asr \
     -F "audio_file=@<audio-file-path>" \
     -F "language=en" \
     -o <output-file-path>
   ```

3. **Verify the output:**
   ```bash
   cat <output-file-path>
   ```

## Supported Audio Formats

| Format | Extension | MIME Type |
|--------|-----------|-----------|
| OGG Vorbis | `.oga`, `.ogg` | `audio/ogg` |
| MP3 | `.mp3` | `audio/mpeg` |
| M4A | `.m4a` | `audio/mp4` |
| WAV | `.wav` | `audio/wav` |
| WebM | `.webm` | `audio/webm` |

## Performance Notes

- The local Whisper service uses the `tiny.en` model
- Processing time is roughly **10-20% of audio duration** (e.g., 1 minute of audio takes ~6-12 seconds)
- The service only supports **English** transcription
- For best results, ensure audio has clear speech with minimal background noise

## Error Handling

Common issues and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| Connection refused | Whisper service not running | Start the local Whisper service using your own deployment method (for example Docker Compose in your chosen whisper-service directory) |
| Empty response | Audio file is silent or corrupted | Check the audio file can be played |
| Garbage text | Audio is not in English | Only English is supported |
| Slow transcription | High CPU load or concurrent requests | Wait for other transcriptions to complete |

## Example: Transcribe a Single File

```bash
# Set variables
AUDIO_FILE="/path/to/recording.wav"
OUTPUT_FILE="${PWD}/transcription.txt"

# Verify service
if ! curl -s http://localhost:9000/health | grep -q '"status": "ok"'; then
    echo "Error: Whisper service is not running"
    exit 1
fi

# Transcribe
curl -X POST http://localhost:9000/asr \
  -F "audio_file=@${AUDIO_FILE}" \
  -F "language=en" \
  -o "$OUTPUT_FILE"

echo "Transcription saved to: $OUTPUT_FILE"
cat "$OUTPUT_FILE"
```

## Example: Batch Transcribe Multiple Files

```bash
for audio_file in *.wav; do
    output_file="${PWD}/$(basename "$audio_file" .wav).txt"
    echo "Transcribing: $audio_file -> $output_file"
    curl -X POST http://localhost:9000/asr \
      -F "audio_file=@${audio_file}" \
      -F "language=en" \
      -o "$output_file"
done
```
