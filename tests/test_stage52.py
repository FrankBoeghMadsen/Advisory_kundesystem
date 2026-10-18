import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path
from unittest.mock import patch

import db
from services.activity_service import dashboard_data, build_dashboard
from services.followup_service import validate_track
from tests.test_db_foundation import isolated_database


ROOT = Path(__file__).resolve().parents[1]


class Stage52Tests(unittest.TestCase):
    def test_followup_dates_and_priority_sort_without_duplicate_events(self):
        rows=[dict(id=1,title='TEST Lav',due_date='2026-10-21',status='Ny',priority='Lav'),
              dict(id=2,title='TEST Høj',due_date='2026-10-21',status='Afventer',priority='Høj'),
              dict(id=3,title='TEST Overskredet',due_date='2026-10-17',status='I gang',priority='Middel'),
              dict(id=4,title='TEST Lukket',due_date='2026-10-21',status='Lukket',priority='Høj')]
        data=build_dashboard(date(2026,10,18),[],[],[],[],[],rows)
        self.assertEqual([a['id'] for a in data['activities']],[3,2,1])
        self.assertEqual(len(data['groups']['Åbne opfølgninger']),3)

    def test_additive_migration_backup_and_restore_preserve_legacy_rows(self):
        with isolated_database() as folder:
            with closing(db.connect()) as conn:
                conn.execute(db.MIGRATION_TABLE_SQL)
                for version,name,migration in db.MIGRATIONS[:6]:
                    migration(conn)
                    conn.execute('INSERT INTO schema_migrations VALUES(?,?,?)',(version,name,db.utc_now_iso()))
                conn.execute("INSERT INTO followups(title,status,created_at) VALUES('TEST Historisk','Lukket','2026-01-01')")
                conn.commit()
                before=dict(conn.execute('SELECT * FROM followups').fetchone())
            db.init_db()
            with closing(db.connect()) as conn:
                after=dict(conn.execute('SELECT * FROM followups').fetchone())
                self.assertEqual({k:after[k] for k in before},before)
                self.assertEqual(after['completed_at'],'')
                self.assertEqual(after['completion_result'],'')
            backup=next((folder/'Backups').glob('*pre_migration*'))
            self.assertEqual(db.applied_migration_versions(backup),{1,2,3,4,5,6})
            self.assertEqual(db.restore_test(backup)['integrity'],'ok')
            self.assertEqual(db.verify_database(db.DB_PATH)['foreign_key_violations'],0)

    def test_completion_retains_links_result_and_disappears_from_dashboard(self):
        with isolated_database():
            from tests.stage4_fixture import populate
            track,proposal,engagement=populate()
            with closing(db.connect()) as conn:
                f=dict(conn.execute('SELECT * FROM followups LIMIT 1').fetchone())
                conn.execute('UPDATE followups SET commercial_track_id=?,deliverable_id=1 WHERE id=?',(track,f['id']))
                conn.execute("UPDATE followups SET status='Lukket',completion_result='TEST Dokumentation modtaget' WHERE id=?",(f['id'],))
                conn.commit()
                closed=dict(conn.execute('SELECT * FROM followups WHERE id=?',(f['id'],)).fetchone())
                self.assertTrue(closed['completed_at'])
                self.assertEqual(closed['completion_result'],'TEST Dokumentation modtaget')
                self.assertEqual(closed['commercial_track_id'],track)
                self.assertEqual(closed['deliverable_id'],1)
                self.assertEqual(closed['company_id'],f['company_id'])
                self.assertNotIn(f['id'],[r['id'] for r in dashboard_data()['groups']['Åbne opfølgninger']])
                conn.execute("UPDATE followups SET status='Lukket',description='TEST Ret note' WHERE id=?",(f['id'],))
                conn.commit()
                self.assertEqual(conn.execute('SELECT completed_at FROM followups WHERE id=?',(f['id'],)).fetchone()[0],closed['completed_at'])
                conn.execute("UPDATE followups SET status='Ny' WHERE id=?",(f['id'],))
                conn.commit()
                reopened=dict(conn.execute('SELECT * FROM followups WHERE id=?',(f['id'],)).fetchone())
                self.assertEqual(reopened['completion_result'],closed['completion_result'])
                self.assertEqual(reopened['completed_at'],closed['completed_at'])
                self.assertIn(f['id'],[r['id'] for r in dashboard_data()['groups']['Åbne opfølgninger']])
                self.assertEqual(validate_track(f['company_id'],track),track)
                with self.assertRaises(ValueError):
                    validate_track(-1,track)

    def test_reload_requires_explicit_development_restart_before_migration(self):
        with isolated_database() as folder:
            with patch.object(db,'APP_MODE','development'), patch.dict(os.environ,{'FRANK_MONITOR_STAGE52_MIGRATION':''}):
                with self.assertRaisesRegex(RuntimeError,'genstart'):
                    db.init_db()
                self.assertFalse(db.DB_PATH.exists())

    def test_ui_close_with_result_link_and_closed_history(self):
        parent=ROOT/'.test-tmp'
        parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent,prefix='stage52-') as directory:
            root=Path(directory)
            runtime=root/'runtime'
            runtime.mkdir()
            env=os.environ.copy()
            env.update(FRANK_MONITOR_MODE='test',FRANK_MONITOR_DATA_DIR=str(root/'data'),
                       FRANK_MONITOR_PRODUCTION_DATA_DIR=str(root/'production'),TEMP=str(runtime),TMP=str(runtime))
            script='''
from streamlit.testing.v1 import AppTest
from tests.stage4_fixture import populate
from db import connect
from services.activity_service import dashboard_data
track,proposal,engagement=populate()
conn=connect()
app=AppTest.from_file('app.py')
app.session_state['page']='Opgaver'
app.run(timeout=30)
app.selectbox(key='followup_new_company').select('TEST Apotek').run()
app.selectbox(key='followup_new_track').select(track).run()
next(t for t in app.text_input if t.label=='Titel').set_value('TEST Dokumentation')
next(b for b in app.button if b.label=='Gem opfølgning').click().run()
fid=conn.execute("SELECT id FROM followups WHERE title='TEST Dokumentation'").fetchone()[0]
app.session_state['record_focus']={'page':'Opgaver','id':fid}
app.run()
app.text_area(key=f'followup_result_{fid}').set_value('TEST Dokumentation modtaget den 22. oktober')
next(b for b in app.button if b.label=='Afslut opfølgning').click().run()
assert not len(app.exception),list(app.exception)
row=conn.execute('SELECT * FROM followups WHERE id=?',(fid,)).fetchone()
assert row['status']=='Lukket' and row['completed_at'] and row['commercial_track_id']==track
assert row['completion_result']=='TEST Dokumentation modtaget den 22. oktober'
assert fid not in [r['id'] for r in dashboard_data()['groups']['Åbne opfølgninger']]
profile=AppTest.from_file('app.py')
profile.session_state['page']='Virksomheder'
profile.session_state['selected_company_id']=int(row['company_id'])
profile.session_state['force_profile_view']=True
profile.session_state[f"profile_section_{row['company_id']}"]='Opfølgning'
profile.run(timeout=30)
assert not len(profile.exception),list(profile.exception)
assert any(row['completion_result'] in x.value for x in profile.markdown)
view=AppTest.from_file('app.py')
view.session_state['page']='Forretning'
view.run(timeout=30)
assert not len(view.exception),list(view.exception)
assert any('TEST Dokumentation' in x.value for x in view.markdown)
view.button(key=f'selected_track_closed_{fid}').click().run()
assert not len(view.exception),list(view.exception)
assert view.text_area(key=f'followup_result_{fid}').value==row['completion_result']
assert not conn.execute('PRAGMA foreign_key_check').fetchall()
conn.close()
'''
            result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
