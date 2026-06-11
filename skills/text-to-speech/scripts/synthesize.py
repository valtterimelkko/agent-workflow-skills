#!/usr/bin/env python3
"""Supertonic TTS synthesis helper script.

Usage:
    python synthesize.py --text "Hello world" --output /tmp/out.wav
    python synthesize.py --text "Hello world" --output /tmp/out.wav --voice F1 --lang en --steps 8 --speed 1.0
    python synthesize.py --input /tmp/text.txt --output /tmp/out.wav
    echo "Hello world" | python synthesize.py --stdin --output /tmp/out.wav
"""

import argparse
import sys
import time
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Supertonic TTS synthesis")
    parser.add_argument("--text", type=str, help="Text to synthesize")
    parser.add_argument("--input", type=str, help="Read text from file")
    parser.add_argument("--stdin", action="store_true", help="Read text from stdin")
    parser.add_argument("--output", "-o", type=str, required=True, help="Output WAV file path")
    parser.add_argument("--voice", type=str, default="M1", help="Voice style: M1-M5, F1-F5 (default: M1)")
    parser.add_argument("--lang", type=str, default=None, help="Language code (en, fr, de, es, ko, ja, etc.)")
    parser.add_argument("--steps", type=int, default=8, help="Quality steps 1-100 (default: 8)")
    parser.add_argument("--speed", type=float, default=1.05, help="Speech speed 0.7-2.0 (default: 1.05)")
    parser.add_argument("--silence", type=float, default=0.3, help="Silence between chunks in seconds (default: 0.3)")
    parser.add_argument("--model", type=str, default="supertonic-3", help="Model name (default: supertonic-3)")
    parser.add_argument("--json", action="store_true", help="Output result as JSON to stdout")
    args = parser.parse_args()

    if not args.text and not args.input and not args.stdin:
        parser.error("Provide --text, --input, or --stdin")

    if args.text:
        text = args.text
    elif args.input:
        text = Path(args.input).read_text().strip()
    elif args.stdin:
        text = sys.stdin.read().strip()

    if not text:
        print("Error: empty text", file=sys.stderr)
        sys.exit(1)

    from supertonic import TTS

    tts = TTS(model=args.model)
    style = tts.get_voice_style(args.voice)

    start = time.time()
    audio, duration = tts.synthesize(
        text,
        voice_style=style,
        total_steps=args.steps,
        speed=args.speed,
        silence_duration=args.silence,
        lang=args.lang,
    )
    elapsed = time.time() - start

    tts.save_audio(audio, args.output)
    audio_duration = float(duration[0]) if hasattr(duration, '__getitem__') else float(duration)

    result = {
        "output_path": str(Path(args.output).resolve()),
        "audio_duration_seconds": round(audio_duration, 2),
        "synthesis_time_seconds": round(elapsed, 2),
        "rtf": round(elapsed / audio_duration, 3),
        "voice": args.voice,
        "lang": args.lang or "auto",
        "steps": args.steps,
        "speed": args.speed,
        "sample_rate": tts.sample_rate,
        "file_size_kb": round(Path(args.output).stat().st_size / 1024, 1),
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Synthesized {audio_duration:.2f}s of audio in {elapsed:.2f}s (RTF {elapsed/audio_duration:.3f}x)")
        print(f"Saved: {args.output} ({result['file_size_kb']:.0f} KB)")


if __name__ == "__main__":
    main()
