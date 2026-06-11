import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import setup as setup_script  # type: ignore


class SetupScriptTests(unittest.TestCase):
    def test_status_json_includes_proxy_and_runtime_fields(self):
        with mock.patch.object(setup_script, "_check_binaries", return_value=[]), mock.patch.object(
            setup_script, "_have_api_key", return_value=True
        ), mock.patch.object(setup_script, "is_first_run", return_value=False), mock.patch.object(
            setup_script, "_have_proxy", return_value=True
        ), mock.patch.object(setup_script, "_detect_js_runtimes", return_value=["deno"]), mock.patch.object(
            setup_script, "_have_browser_cookies", return_value=False
        ):
            status = setup_script._status()

        self.assertIn("has_proxy", status)
        self.assertIn("js_runtimes", status)
        self.assertIn("cookies_available", status)
        self.assertEqual(status["js_runtimes"], ["deno"])


if __name__ == "__main__":
    unittest.main()
