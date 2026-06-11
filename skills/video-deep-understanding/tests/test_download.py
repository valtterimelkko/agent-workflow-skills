import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import download  # type: ignore


class DownloadScriptTests(unittest.TestCase):
    def test_cached_url_download_reuses_existing_local_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cache_root = tmp_path / "cache"
            cache_index = cache_root / "index.json"
            cache_root.mkdir(parents=True, exist_ok=True)

            video_path = tmp_path / "cached-video.mp4"
            subtitle_path = tmp_path / "cached-video.en.vtt"
            video_path.write_bytes(b"video")
            subtitle_path.write_text("WEBVTT\n")
            cache_index.write_text(
                json.dumps(
                    {
                        "https://example.com/watch": {
                            "video_path": str(video_path),
                            "subtitle_path": str(subtitle_path),
                            "info": {"title": "Cached title", "url": "https://example.com/watch"},
                        }
                    }
                )
            )

            with mock.patch.object(download, "CACHE_ROOT", cache_root), mock.patch.object(
                download, "CACHE_INDEX_PATH", cache_index
            ), mock.patch.object(
                download.subprocess,
                "run",
                side_effect=AssertionError("yt-dlp should not run when cache hit is valid"),
            ):
                result = download.download_url("https://example.com/watch", tmp_path / "out")

            self.assertTrue(result["cache_hit"])
            self.assertEqual(result["video_path"], str(video_path))
            self.assertEqual(result["subtitle_path"], str(subtitle_path))

    def test_classify_yt_dlp_failure_highlights_bot_challenge(self):
        message = download.classify_yt_dlp_failure(
            "ERROR: Sign in to confirm you’re not a bot"
        )
        self.assertIn("bot challenge", message.lower())
        self.assertIn("proxy", message.lower())


if __name__ == "__main__":
    unittest.main()
