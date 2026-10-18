import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import db
from services.project_service import save_project, save_participant, save_workstream, link_track, remove_relation
from tests.stage61_fixture import populate
from tests.test_db_foundation import isolated_database

ROOT=Path(__file__).resolve().parents[1]


class Stage61Tests(unittest.TestCase):
    def test_optional_project_roles_and_streams_create_no_commercial_records(self):
        with isolated_database():
            a,b,track=populate()
            with closing(db.connect()) as conn:
                before={t:[tuple(r) for r in conn.execute(f'SELECT * FROM {t}')] for t in ('commercial_tracks','proposals','engagements','deliverables','followups')}
            p=save_project('TEST Projekt uden aftale')
            save_participant(p,a,['Koordinator','Aftalepart','Betaler','Deltager'])
            save_participant(p,b,[])
            common=save_workstream(p,'TEST Fælles')
            own=save_workstream(p,'TEST Analyse',b,'I gang')
            save_workstream(p,'TEST Analyse revideret',b,'Afsluttet',own)
            save_project('TEST Opdateret','TEST Formål','Aktivt',p)
            with closing(db.connect()) as conn:
                for t,rows in before.items():
                    self.assertEqual([tuple(r) for r in conn.execute(f'SELECT * FROM {t}')],rows)
                role=conn.execute('SELECT * FROM project_companies WHERE project_id=? AND company_id=?',(p,a)).fetchone()
                self.assertEqual((role['coordinator'],role['contracting_party'],role['payer'],role['participant']),(1,1,1,1))
                self.assertIsNone(conn.execute('SELECT company_id FROM project_workstreams WHERE id=?',(common,)).fetchone()[0])
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM project_tracks').fetchone()[0],0)
                self.assertEqual(conn.execute('PRAGMA foreign_keys').fetchone()[0],0)
                self.assertFalse(conn.execute('PRAGMA foreign_key_check').fetchall())

    def test_validation_links_and_safe_removal(self):
        with isolated_database():
            a,b,track=populate()
            p=save_project('TEST Projekt')
            other=save_project('TEST Andet')
            for args in [('',),('TEST','','Forkert')]:
                with self.assertRaises(ValueError): save_project(*args)
            with self.assertRaises(ValueError): save_participant(p,999,['Deltager'])
            with self.assertRaises(ValueError): save_participant(p,a,['Forkert'])
            with self.assertRaises(ValueError): save_workstream(p,'TEST',a)
            with self.assertRaises(ValueError): link_track(p,track)
            save_participant(p,a,['Deltager'])
            link_track(p,track)
            link_track(p,track)
            save_participant(other,a,[])
            with self.assertRaises(ValueError): link_track(other,track)
            with self.assertRaises(ValueError): remove_relation('participant',p,a)
            sid=save_workstream(p,'TEST Spor',a)
            with self.assertRaises(ValueError): save_workstream(other,'TEST',None,'Planlagt',sid)
            remove_relation('track',p,track)
            with self.assertRaises(ValueError): remove_relation('participant',p,a)
            remove_relation('workstream',p,sid)
            remove_relation('participant',p,a)
            link_track(other,track)
            with closing(db.connect()) as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM commercial_tracks').fetchone()[0],1)
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM project_tracks').fetchone()[0],1)

    def test_database_guards_work_even_on_legacy_connections_without_fk(self):
        with isolated_database():
            a,b,track=populate()
            p=save_project('TEST Projekt')
            save_participant(p,a,[])
            sid=save_workstream(p,'TEST Spor',a)
            link_track(p,track)
            with closing(db.connect()) as conn:
                invalid=[
                    ('INSERT INTO project_companies(project_id,company_id) VALUES(?,?)',(999,a)),
                    ('INSERT INTO project_tracks(project_id,track_id) VALUES(?,?)',(p,999)),
                    ('UPDATE project_workstreams SET company_id=? WHERE id=?',(b,sid)),
                    ('UPDATE project_companies SET company_id=? WHERE project_id=?',(b,p)),
                    ('DELETE FROM projects WHERE id=?',(p,)),
                    ('DELETE FROM companies WHERE id=?',(a,)),
                    ('DELETE FROM commercial_tracks WHERE id=?',(track,)),
                    ('UPDATE commercial_tracks SET company_id=? WHERE id=?',(b,track)),
                    ('UPDATE projects SET id=999 WHERE id=?',(p,)),
                    ('UPDATE companies SET id=999 WHERE id=?',(a,)),
                    ('UPDATE commercial_tracks SET id=999 WHERE id=?',(track,)),
                    ("UPDATE project_workstreams SET status='Forkert' WHERE id=?",(sid,)),
                ]
                for sql,args in invalid:
                    with self.assertRaises(sqlite3.IntegrityError,msg=sql): conn.execute(sql,args)
                    conn.rollback()
                self.assertFalse(conn.execute('PRAGMA foreign_key_check').fetchall())

    def test_version7_migration_backup_and_rollback(self):
        with isolated_database() as folder:
            with closing(db.connect()) as conn:
                conn.execute(db.MIGRATION_TABLE_SQL)
                for version,name,migration in db.MIGRATIONS[:7]:
                    migration(conn)
                    conn.execute('INSERT INTO schema_migrations VALUES(?,?,?)',(version,name,db.utc_now_iso()))
                conn.execute("INSERT INTO companies(name,created_at) VALUES('TEST Historik','2026-01-01')")
                conn.execute("INSERT INTO followups(company_id,title,status,completed_at,completion_result,created_at) VALUES(1,'TEST Lukket','Lukket','2026-01-02','TEST Bevaret','2026-01-01')")
                conn.commit()
                before={t:[tuple(r) for r in conn.execute(f'SELECT * FROM {t}')] for t in ('companies','contacts','commercial_tracks','proposals','engagements','deliverables','meetings','followups')}
            db.init_db()
            with closing(db.connect()) as conn:
                for t,rows in before.items(): self.assertEqual([tuple(r) for r in conn.execute(f'SELECT * FROM {t}')],rows)
                for t in ('projects','project_companies','project_workstreams','project_tracks'):
                    self.assertEqual(conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0],0)
            backup=next((folder/'Backups').glob('*pre_migration*'))
            self.assertEqual(db.applied_migration_versions(backup),set(range(1,8)))
            self.assertEqual(db.restore_test(backup)['integrity'],'ok')
            self.assertEqual(db.verify_database(db.DB_PATH)['foreign_key_violations'],0)

    def test_reload_guard_stops_before_writes(self):
        with isolated_database():
            with patch.object(db,'APP_MODE','development'),patch.dict(os.environ,{'FRANK_MONITOR_STAGE61_MIGRATION':''}):
                with self.assertRaisesRegex(RuntimeError,'6.1'): db.init_db()
                self.assertFalse(db.DB_PATH.exists())

    def test_project_ui_and_direct_navigation(self):
        parent=ROOT/'.test-tmp'
        parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent,prefix='stage61-ui-') as directory:
            root=Path(directory)
            runtime=root/'runtime'
            runtime.mkdir()
            env=os.environ.copy()
            env.update(FRANK_MONITOR_MODE='test',FRANK_MONITOR_DATA_DIR=str(root/'data'),FRANK_MONITOR_PRODUCTION_DATA_DIR=str(root/'production'),TEMP=str(runtime),TMP=str(runtime))
            script='''
from streamlit.testing.v1 import AppTest
from tests.stage61_fixture import populate
from db import connect
from services.project_service import save_participant,link_track
a,b,track=populate()
app=AppTest.from_file('app.py')
app.session_state['page']='Forretning'
app.run(timeout=30)
app.radio(key='business_view').set_value('Projekter').run()
app.button(key='project_create_open').click().run()
next(x for x in app.button if x.label=='Opret projekt' and x.key!='project_create_open').click().run()
assert len(app.error)
next(x for x in app.text_input if x.label=='Projekttitel').set_value('TEST Nyt projekt')
next(x for x in app.button if x.label=='Opret projekt' and x.key!='project_create_open').click().run()
assert not len(app.exception),list(app.exception)
p=app.session_state['project_selected']
app.button(key=f'project_member_open_{p}').click().run()
next(x for x in app.selectbox if x.label=='Virksomhed').select(a)
next(x for x in app.multiselect if x.label=='Projektroller').set_value(['Koordinator','Betaler'])
next(x for x in app.button if x.label=='Gem deltager').click().run()
app.button(key=f'project_stream_open_{p}').click().run()
next(x for x in app.text_input if x.label=='Sportitel').set_value('TEST Fælles spor')
next(x for x in app.button if x.label=='Gem arbejdsspor').click().run()
assert not len(app.exception),list(app.exception)
app.button(key=f'project_link_open_{p}').click().run()
next(x for x in app.selectbox if x.label=='Eksisterende forløb').select(track)
next(x for x in app.button if x.label=='Tilknyt forløb').click().run()
assert not len(app.exception),list(app.exception)
app.button(key=f'project_open_track_{track}').click().run()
assert not len(app.exception),list(app.exception)
assert app.radio(key='business_view').value=='Forløb'
assert app.radio(key='business_section').value=='Pipeline'
conn=connect()
assert conn.execute('SELECT COUNT(*) FROM projects').fetchone()[0]==1
assert conn.execute('SELECT COUNT(*) FROM project_workstreams').fetchone()[0]==1
assert conn.execute('SELECT COUNT(*) FROM proposals').fetchone()[0]==0
assert conn.execute('SELECT COUNT(*) FROM engagements').fetchone()[0]==0
assert not conn.execute('PRAGMA foreign_key_check').fetchall()
before=list(conn.iterdump())
view=AppTest.from_file('app.py')
view.session_state['page']='Forretning'
view.session_state['business_view']='Projekter'
view.session_state['project_selected']=p
view.run(timeout=30)
view.run()
assert not len(view.exception),list(view.exception)
assert list(conn.iterdump())==before
conn.close()
'''
            result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
