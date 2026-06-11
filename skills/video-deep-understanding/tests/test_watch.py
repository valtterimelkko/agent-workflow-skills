import io
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import watch  # type: ignore


class WatchScriptTests(unittest.TestCase):
    def test_transcript_only_mode_skips_frame_extraction_and_reports_mode(self):
        fake_segments = [{"start": 0.0, "end": 1.0, "text": "kanban intro"}]
        stdout = io.StringIO()
        stderr = io.StringIO()

        with mock.patch.object(
            sys,
            "argv",
            ["watch.py", "/tmp/fake.mp4", "--transcript-only"],
        ), mock.patch.object(
            watch,
            "download",
            return_value={
                "video_path": "/tmp/fake.mp4",
                "subtitle_path": "/tmp/fake.vtt",
                "info": {"title": "Test video"},
            },
        ), mock.patch.object(
            watch,
            "get_metadata",
            return_value={"duration_seconds": 12.0, "width": 640, "height": 360, "codec": "h264"},
        ), mock.patch.object(
            watch,
            "parse_vtt",
            return_value=fake_segments,
        ), mock.patch.object(
            watch,
            "extract",
            side_effect=AssertionError("extract should not be called in transcript-only mode"),
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            rc = watch.main()

        self.assertEqual(rc, 0)
        report = stdout.getvalue()
        self.assertIn("- **Mode:** transcript-only", report)
        self.assertIn("kanban intro", report)

    def test_find_option_surfaces_transcript_matches(self):
        fake_segments = [
            {"start": 0.0, "end": 1.0, "text": "intro"},
            {"start": 12.0, "end": 13.0, "text": "kanban board with retry history"},
        ]
        stdout = io.StringIO()
        stderr = io.StringIO()

        with mock.patch.object(
            sys,
            "argv",
            ["watch.py", "/tmp/fake.mp4", "--transcript-only", "--find", "kanban|retry"],
        ), mock.patch.object(
            watch,
            "download",
            return_value={
                "video_path": "/tmp/fake.mp4",
                "subtitle_path": "/tmp/fake.vtt",
                "info": {"title": "Test video"},
            },
        ), mock.patch.object(
            watch,
            "get_metadata",
            return_value={"duration_seconds": 20.0, "width": 640, "height": 360, "codec": "h264"},
        ), mock.patch.object(
            watch,
            "parse_vtt",
            return_value=fake_segments,
        ), mock.patch.object(
            watch,
            "extract",
            side_effect=AssertionError("extract should not be called in transcript-only mode"),
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            rc = watch.main()

        self.assertEqual(rc, 0)
        report = stdout.getvalue()
        self.assertIn("## Transcript matches", report)
        self.assertIn("kanban board with retry history", report)


if __name__ == "__main__":
    unittest.main()
