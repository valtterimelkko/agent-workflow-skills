---
name: text-to-speech
description: "Convert text to natural-sounding speech audio using Supertonic — a fully local, CPU-only, ONNX-based TTS engine supporting 31 languages and 10 voice styles. Use this skill whenever the user wants to generate audio from text, create voice recordings, add speech to videos, narrate content, produce podcasts, create TTS for apps, convert documents to audio, or mentions text-to-speech / TTS / speech synthesis / voice generation / audio narration. Works on any CPU — no GPU or cloud needed."
---

# Text-to-Speech (Supertonic)

Supertonic is a fully local text-to-speech engine that converts any text into studio-quality 44.1kHz WAV audio. It runs entirely on CPU via ONNX Runtime — no GPU, no cloud API, no network needed after the initial ~404 MB model download. It synthesizes audio 3-4x faster than real-time on a typical server CPU.

## System Requirements

- Python 3.8+
- ~500 MB RAM for model loading
- ~404 MB disk for model files (auto-downloaded on first use)
- No GPU required

## Installation

```bash
pip install supertonic
```

On Ubuntu 24.04+ (PEP 668):
```bash
pip install supertonic --break-system-packages
```

Models auto-download from Hugging Face on first synthesis. Cached at `~/.cache/supertonic3/`.

## Quick Start — Python API

```python
from supertonic import TTS
import soundfile as sf

tts = TTS()  # loads supertonic-3 (31 languages)
style = tts.get_voice_style("M1")  # male voice
audio, duration = tts.synthesize("Hello, world!", voice_style=style)
sf.write("output.wav", audio.squeeze(), tts.sample_rate)
```

The bundled script at `scripts/synthesize.py` wraps this into a one-liner:

```bash
python scripts/synthesize.py --text "Hello, world!" --output output.wav
```

## API Reference

### Initialization

```python
tts = TTS(
    model="supertonic-3",     # "supertonic" (en), "supertonic-2" (5 langs), "supertonic-3" (31 langs)
    model_dir=None,           # override model cache directory
    auto_download=True,       # auto-download missing models
    intra_op_num_threads=None, # ONNX thread count (None = auto)
    inter_op_num_threads=None, # ONNX thread count (None = auto)
)
```

### Synthesis

```python
audio, duration = tts.synthesize(
    text,                     # text string (up to 100,000 chars)
    voice_style=style,        # Style object from get_voice_style()
    total_steps=8,            # quality: 5=fast, 8=balanced, 12=high
    speed=1.05,               # speech speed: 0.7 (slow) to 2.0 (fast)
    max_chunk_length=None,    # chars per chunk (default: 300, Korean: 120)
    silence_duration=0.3,     # seconds of silence between chunks
    lang=None,                # language code or None for auto
    verbose=False,            # print progress
)
# audio: numpy array shape (1, num_samples), float32
# duration: numpy array with total seconds
```

### Voice Styles

10 built-in voices:
- **Male**: M1 (default), M2, M3, M4, M5
- **Female**: F1, F2, F3, F4, F5

```python
style = tts.get_voice_style("M1")       # by name
style = tts.get_voice_style_from_path("custom.json")  # custom voice file
```

### Saving Audio

```python
tts.save_audio(audio, "output.wav")  # uses the built-in method
# OR manually with soundfile:
import soundfile as sf
sf.write("output.wav", audio.squeeze(), tts.sample_rate)
```

### Supported Languages (supertonic-3)

`en`, `ko`, `ja`, `ar`, `bg`, `cs`, `da`, `de`, `el`, `es`, `et`, `fi`, `fr`, `hi`, `hr`, `hu`, `id`, `it`, `lt`, `lv`, `nl`, `pl`, `pt`, `ro`, `ru`, `sk`, `sl`, `sv`, `tr`, `uk`, `vi`

Special code `na` = unknown language fallback (model tries its best without language-specific tokens).

### CLI

```bash
supertonic tts "Hello!" -o hello.wav                    # save to file
supertonic say "Hello!"                                  # play directly (needs sounddevice)
supertonic tts "Bonjour!" -o fr.wav --lang fr --voice F1
supertonic tts "Long text..." -o out.wav --steps 12 --speed 1.2
supertonic list-voices                                   # show available voices
supertonic info                                          # show model info
```

## Common Patterns

### Generate audio for a video voiceover

```python
from supertonic import TTS
import soundfile as sf

tts = TTS()
style = tts.get_voice_style("F1")
script = Path("voiceover.txt").read_text()
audio, dur = tts.synthesize(script, voice_style=style, speed=1.0, steps=10)
sf.write("voiceover.wav", audio.squeeze(), tts.sample_rate)
print(f"Generated {dur[0]:.1f}s of audio")
```

### Batch synthesis — multiple files

```python
from supertonic import TTS
import soundfile as sf

tts = TTS()
style = tts.get_voice_style("M2")

segments = [
    ("intro", "Welcome to our presentation."),
    ("middle", "Let's dive into the data."),
    ("outro", "Thank you for listening."),
]

for name, text in segments:
    audio, _ = tts.synthesize(text, voice_style=style)
    sf.write(f"{name}.wav", audio.squeeze(), tts.sample_rate)
```

### Using the bundled script

```bash
# Simple
python scripts/synthesize.py --text "Hello world" --output /tmp/hello.wav

# From file
python scripts/synthesize.py --input script.txt --output narration.wav --voice F2 --steps 10

# With JSON output for programmatic use
python scripts/synthesize.py --text "Test" --output /tmp/test.wav --json

# Piped input
echo "Hello from stdin" | python scripts/synthesize.py --stdin --output /tmp/piped.wav
```

### Convert to MP3 (if ffmpeg available)

```bash
ffmpeg -i output.wav -codec:a libmp3lame -qscale:a 2 output.mp3
```

## Performance Tuning

- **total_steps**: The main quality/speed knob. Default 8 is a good balance. Use 5 for draft/preview, 12 for final output. Diminishing returns above 12.
- **speed**: 1.05 is the natural default. 1.3-1.5 for informational content, 0.8-0.9 for dramatic effect.
- **Threading**: Set `SUPERTONIC_INTRA_OP_THREADS` and `SUPERTONIC_INTER_OP_THREADS` env vars to control ONNX parallelism. Default (None) lets ONNX auto-detect, which is usually optimal.
- **Long text**: Text is auto-chunked at 300 chars (120 for Korean). Adjust `max_chunk_length` if needed.

## Integration Notes

- The `synthesize()` return is `(audio_array, duration_array)` — both are numpy arrays. Use `audio.squeeze()` for writing.
- `save_audio()` accepts the audio array directly (not the tuple). Pass `audio` not `(audio, duration)`.
- Reuse the `TTS()` instance across calls — model loading takes ~1s and should happen once.
- For web apps: the package also has JavaScript/browser examples in its GitHub repo using `onnxruntime-web`.
- License: MIT (code), OpenRAIL-M (model weights) — permissive for commercial use.
