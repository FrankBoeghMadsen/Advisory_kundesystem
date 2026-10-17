import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app_config import PAGE_OPTIONS
from views import VIEW_RENDERERS


ROOT = Path(__file__).resolve().parents[1]
TEST_TEMP_ROOT = ROOT / ".test-tmp"
PAGES = PAGE_OPTIONS


class AppViewTests(unittest.TestCase):
    def test_every_navigation_option_has_a_renderer(self):
        self.assertEqual(set(PAGES), set(VIEW_RENDERERS))

    def test_all_navigation_views_render_without_exceptions(self):
        TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="frank-monitor-ui-", dir=TEST_TEMP_ROOT
        ) as temp_dir:
            temp_path = Path(temp_dir)
            runtime_temp = temp_path / "runtime"
            runtime_temp.mkdir()
            env = os.environ.copy()
            env["FRANK_MONITOR_DATA_DIR"] = str(temp_path / "data")
            env["TEMP"] = str(runtime_temp)
            env["TMP"] = str(runtime_temp)
            page_literal = repr(PAGES)
            script = f"""
from streamlit.testing.v1 import AppTest

for page in {page_literal}:
    app = AppTest.from_file('app.py')
    app.session_state['page'] = page
    app.run(timeout=30)
    if len(app.exception):
        raise AssertionError(f'{{page}}: {{list(app.exception)}}')
print('rendered={len(PAGES)}')
"""
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(f"rendered={len(PAGES)}", result.stdout)


if __name__ == "__main__":
    unittest.main()
