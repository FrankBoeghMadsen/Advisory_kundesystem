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
    def test_stage4_interactive_fee_form_and_read_only_page(self):
        TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='stage4-ui-', dir=TEST_TEMP_ROOT) as directory:
            root = Path(directory)
            env = os.environ.copy()
            env['FRANK_MONITOR_MODE'] = 'test'
            env['FRANK_MONITOR_DATA_DIR'] = str(root / 'data')
            env['FRANK_MONITOR_PRODUCTION_DATA_DIR'] = str(root / 'production')
            script = '''
from streamlit.testing.v1 import AppTest
from tests.stage4_fixture import populate
from db import connect

track, accepted, engagement = populate()
conn = connect()
before = [tuple(row) for row in conn.execute('SELECT * FROM proposals ORDER BY id')]
app = AppTest.from_file('app.py')
app.session_state['page'] = 'Forretning'
app.run(timeout=30)
assert not len(app.exception), list(app.exception)
assert [tuple(row) for row in conn.execute('SELECT * FROM proposals ORDER BY id')] == before
assert app.selectbox(key='track_new_company').value is None
assert not any('honorar er angivet' in item.label for item in app.checkbox)

prefix = f'proposal_{track}_new'
app.selectbox(key=prefix+'_model').select('Fast pris').run()
assert not app.text_input(key=prefix+'_amount').disabled
assert app.text_input(key=prefix+'_amount').value == ''
app.text_input(key=prefix+'_title').set_value('Nyt fastpristilbud')
app.text_input(key=prefix+'_amount').set_value('12.500,50')
app.button(key=prefix+'_save').click().run()
assert not len(app.exception), list(app.exception)
row = conn.execute("SELECT * FROM proposals WHERE title='Nyt fastpristilbud'").fetchone()
assert row['offered_fee_ex_vat'] == 12500.5
assert row['valid_until'] == '' and row['sent_date'] == ''
app.selectbox(key=prefix+'_model').select('Timepris').run()
assert app.text_input(key=prefix+'_hours').value == ''
assert app.text_input(key=prefix+'_cap').value == ''
app.text_input(key=prefix+'_title').set_value('Timepristilbud')
app.text_input(key=prefix+'_amount').set_value('1.800,00')
app.text_input(key=prefix+'_hours').set_value('10')
app.text_input(key=prefix+'_cap').set_value('18.000')
app.button(key=prefix+'_save').click().run()
assert not len(app.exception), list(app.exception)
row = conn.execute("SELECT * FROM proposals WHERE title='Timepristilbud'").fetchone()
assert (row['offered_fee_ex_vat'], row['max_hours'], row['fee_cap_ex_vat']) == (1800,10,18000)
assert not any(item.key == f'proposal_{track}_{accepted}_title' for item in app.text_input)
app.checkbox(key=f'correct_{accepted}').check().run()
correction = f'proposal_{track}_{accepted}'
app.text_input(key=correction+'_amount').set_value('24.000')
app.text_area(key=correction+'_reason').set_value('Rettelse af testregistrering')
app.button(key=correction+'_save').click().run()
assert not len(app.exception), list(app.exception)
assert conn.execute('SELECT offered_fee_ex_vat FROM proposals WHERE id=?',(accepted,)).fetchone()[0] == 24000
assert conn.execute('SELECT COUNT(*) FROM proposal_changes WHERE proposal_id=?',(accepted,)).fetchone()[0] == 1
app.text_area(key=f'amendment_desc_{engagement}').set_value('Syntetisk udvidelse')
app.text_input(key=f'amendment_fee_{engagement}').set_value('27.000')
app.text_input(key=f'amendment_ref_{engagement}').set_value('TEST accept')
app.button(key=f'amendment_save_{engagement}').click().run()
assert not len(app.exception), list(app.exception)
assert conn.execute('SELECT agreed_fee_ex_vat FROM engagements WHERE id=?',(engagement,)).fetchone()[0] == 27000
conn.close()
print('stage4-interactive=ok')
'''
            result = subprocess.run([sys.executable,'-c',script], cwd=ROOT, env=env,
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('stage4-interactive=ok',result.stdout)

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
            env["FRANK_MONITOR_MODE"] = "test"
            env["FRANK_MONITOR_DATA_DIR"] = str(temp_path / "data")
            env["FRANK_MONITOR_PRODUCTION_DATA_DIR"] = str(temp_path / "production-must-not-be-used")
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

    def test_business_view_renders_with_synthetic_commercial_data(self):
        TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="frank-monitor-business-ui-", dir=TEST_TEMP_ROOT
        ) as temp_dir:
            temp_path = Path(temp_dir)
            runtime_temp = temp_path / "runtime"
            runtime_temp.mkdir()
            env = os.environ.copy()
            env["FRANK_MONITOR_MODE"] = "test"
            env["FRANK_MONITOR_DATA_DIR"] = str(temp_path / "data")
            env["FRANK_MONITOR_PRODUCTION_DATA_DIR"] = str(temp_path / "production-must-not-be-used")
            env["TEMP"] = str(runtime_temp)
            env["TMP"] = str(runtime_temp)
            script = """
from streamlit.testing.v1 import AppTest
from db import connect, init_db, utc_now_iso

init_db()
now = utc_now_iso()
conn = connect()
actor = conn.execute("INSERT INTO companies (name, created_at) VALUES ('TEST UI Aktør', ?)", (now,)).lastrowid
contact = conn.execute("INSERT INTO contacts (company_id, name, created_at) VALUES (?, 'Testkontakt', ?)", (actor, now)).lastrowid
track = conn.execute("INSERT INTO commercial_tracks (company_id, primary_contact_id, title, status, created_at, updated_at) VALUES (?, ?, 'Testforløb', 'Afventer', ?, ?)", (actor, contact, now, now)).lastrowid
proposal = conn.execute("INSERT INTO proposals (track_id, title, version, fee_model, offered_fee_ex_vat, status, created_at, updated_at) VALUES (?, 'Testtilbud', 1, 'Fast pris', 10000, 'Afventer', ?, ?)", (track, now, now)).lastrowid
engagement = conn.execute("INSERT INTO engagements (track_id, accepted_proposal_id, title, fee_model, agreed_fee_ex_vat, status, created_at, updated_at) VALUES (?, ?, 'Testopgave', 'Fast pris', 9500, 'I gang', ?, ?)", (track, proposal, now, now)).lastrowid
conn.execute("INSERT INTO deliverables (engagement_id, title, due_date, status, created_at, updated_at) VALUES (?, 'Testleverance', '2026-12-01', 'I gang', ?, ?)", (engagement, now, now))
conn.commit()
conn.close()

app = AppTest.from_file('app.py')
app.session_state['page'] = 'Forretning'
app.run(timeout=30)
if len(app.exception):
    raise AssertionError(list(app.exception))
assert any(item.value == 'Forretning' for item in app.subheader)
print('business-ui=ok')
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
            self.assertIn("business-ui=ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
