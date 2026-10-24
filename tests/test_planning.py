import json
import sqlite3
import unittest
from contextlib import closing
from datetime import date
from unittest.mock import patch

import db
from services.acceptance_service import document_acceptance
from services.business_service import save_business_record, create_engagement_from_proposal
from services.planning_service import (save_work_block, delete_work_block, set_capacity, week_data,
    danish_date, local_today)
from services.activity_service import dashboard_data, activity_urgency
from tests.stage61_fixture import populate
from tests.test_db_foundation import isolated_database
from tests import test_stage61a


def fixture():
    a,b,t=populate()
    e=save_business_record('engagements',dict(track_id=t,title='TEST Kundeopgave',status='I gang'))
    d=save_business_record('deliverables',dict(engagement_id=e,title='TEST Leverance',status='I gang',due_date='2026-10-28'))
    return t,e,d


class PlanningTests(unittest.TestCase):
    def test_blocks_capacity_weekend_deadlines_and_parent_guards(self):
        with isolated_database():
            t,e,d=fixture()
            b=save_work_block('2026-10-26',e,d,'TEST Første',5)
            save_work_block('2026-10-27',e,d,'TEST Anden',9)
            save_work_block('2026-10-31',e,None,'TEST Weekend',2)
            week=week_data(date(2026,10,28))
            self.assertEqual(week['planned'],16*60)
            self.assertEqual(week['capacity'],35*60)
            self.assertEqual(week['days'][1]['remaining'],-120)
            self.assertEqual(week['days'][5]['remaining'],-120)
            self.assertEqual(len(week['days'][2]['deadlines']),1)
            self.assertEqual(week['days'][2]['planned'],0)
            set_capacity('2026-10-31',4)
            self.assertEqual(week_data(date(2026,10,28))['days'][5]['remaining'],120)
            save_work_block('2026-10-29',e,d,'TEST Flyttet',3,record_id=b)
            self.assertEqual(len(week_data(date(2026,10,28))['days'][3]['after_deadline']),1)
            with closing(db.connect()) as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM work_blocks').fetchone()[0],3)
                for sql in ('DELETE FROM engagements WHERE id=?','DELETE FROM deliverables WHERE id=?'):
                    with self.assertRaises(sqlite3.IntegrityError):
                        conn.execute(sql,(e if 'engagements' in sql else d,))
                    conn.rollback()
                other=save_business_record('engagements',dict(track_id=t,title='TEST Anden opgave'))
                with self.assertRaises(ValueError):
                    save_work_block('2026-10-26',other,d,'TEST Forkert relation',1)
            delete_work_block(b)
            self.assertEqual(week_data(date(2026,10,28))['planned'],11*60)
            self.assertEqual(db.verify_database(db.DB_PATH)['foreign_key_violations'],0)

    def test_validation_completed_deliveries_and_local_date(self):
        with isolated_database():
            t,e,d=fixture()
            for value in (0,-1,float('nan'),float('inf'),0.001):
                with self.assertRaises(ValueError):
                    save_work_block('2026-10-26',e,d,'TEST Ugyldig',value)
            with self.assertRaises(ValueError):
                set_capacity('ikke en dato',7)
            with self.assertRaises(ValueError):
                set_capacity('2026-10-26',-1)
            set_capacity('2026-10-26',0)
            save_business_record('deliverables',dict(title='TEST Leveret',status='Leveret',due_date='2026-10-20'),d)
            self.assertFalse(any(x['kind']=='Leverancefrist' for x in dashboard_data(date(2026,10,25))['activities']))
            self.assertFalse(week_data(date(2026,10,20))['days'][1]['deadlines'])
            expected=dict(binding=False,day=date(2026,10,20),kind='Forventet beslutning')
            self.assertEqual(activity_urgency(expected,date(2026,10,25))[1],'neutral')
            self.assertEqual(activity_urgency(dict(expected,binding=True,kind='Leverancefrist'),date(2026,10,25))[1],'red')
            self.assertEqual(danish_date(date(2026,10,25)),'Søndag 25. oktober 2026')
            with patch('services.planning_service.datetime') as clock:
                from datetime import datetime, timezone
                clock.now.side_effect=lambda zone:datetime(2026,10,24,23,30,tzinfo=timezone.utc).astimezone(zone)
                self.assertEqual(local_today(),date(2026,10,25))

    def test_acceptance_history_and_original_agreement(self):
        with isolated_database():
            a,b,t=populate()
            p=save_business_record('proposals',dict(track_id=t,title='TEST Tilbud',version=1,status='Sendt',offered_fee_ex_vat=20000))
            evidence=dict(acceptance_date='2026-10-24',acceptance_method='E-mail',document_reference='TEST accept.pdf',note='TEST Note')
            e=create_engagement_from_proposal(p,'TEST Opgave','','I gang','','','Fast pris',20000,'',acceptance=evidence)
            with closing(db.connect()) as conn:
                before=dict(conn.execute('SELECT * FROM engagements WHERE id=?',(e,)).fetchone())
                self.assertEqual(json.loads(before['original_agreement'])['acceptance_documentation'],evidence)
                self.assertEqual(json.loads(before['accepted_proposal_snapshot'])['acceptance_documentation'],evidence)
            document_acceptance(p,dict(evidence,note='TEST Supplering'))
            with closing(db.connect()) as conn:
                self.assertEqual(dict(conn.execute('SELECT * FROM engagements WHERE id=?',(e,)).fetchone()),before)
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM proposal_acceptances').fetchone()[0],2)
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute('DELETE FROM proposal_acceptances')
            with self.assertRaises(ValueError):
                document_acceptance(p,dict(acceptance_date='2026-02-31'))
            with self.assertRaises(ValueError):
                create_engagement_from_proposal(p,'TEST Dublet','','I gang','','','Fast pris',20000,'')
            draft=save_business_record('proposals',dict(track_id=t,title='TEST Ikke accepteret',version=2,status='Sendt'))
            with self.assertRaises(ValueError):
                create_engagement_from_proposal(draft,'TEST Ugyldig','','I gang','','','Fast pris',0,'',acceptance={'acceptance_date':'2026-02-31'})
            with closing(db.connect()) as conn:
                self.assertEqual(conn.execute('SELECT status FROM proposals WHERE id=?',(draft,)).fetchone()[0],'Sendt')
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM engagements').fetchone()[0],1)
            prior=save_business_record('proposals',dict(track_id=t,title='TEST Accept før opgave',version=3,status='Accepteret'))
            document_acceptance(prior,evidence)
            inherited=create_engagement_from_proposal(prior,'TEST Genbrug accept','','I gang','','','Fast pris',0,'')
            with closing(db.connect()) as conn:
                original=json.loads(conn.execute('SELECT original_agreement FROM engagements WHERE id=?',(inherited,)).fetchone()[0])
                self.assertEqual(original['acceptance_documentation'],evidence)
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM proposal_acceptances WHERE proposal_id=?',(prior,)).fetchone()[0],1)

    def test_migration_backup_restore_and_development_reload_guard(self):
        with isolated_database() as folder:
            with closing(db.connect()) as conn:
                conn.execute(db.MIGRATION_TABLE_SQL)
                for version,name,migration in db.MIGRATIONS[:8]:
                    migration(conn)
                    conn.execute('INSERT INTO schema_migrations VALUES(?,?,?)',(version,name,db.utc_now_iso()))
                conn.execute("INSERT INTO companies(name,created_at) VALUES('TEST Bevar','2026-10-01')")
                conn.commit()
                before=[tuple(r) for r in conn.execute('SELECT * FROM companies')]
            with patch.object(db,'APP_MODE','development'),patch.dict('os.environ',{},clear=True):
                with self.assertRaisesRegex(RuntimeError,'Ugeplanlægning'):
                    db.init_db()
            with patch.object(db,'APP_MODE','production'),patch.object(db,'PRODUCTION_DATA_DIR',folder):
                with self.assertRaisesRegex(RuntimeError,'afventer godkendelse'):
                    db.init_db()
            self.assertEqual(db.applied_migration_versions(db.DB_PATH),set(range(1,9)))
            db.init_db()
            backup=next((folder/'Backups').glob('*pre_migration*'))
            self.assertEqual(db.applied_migration_versions(backup),set(range(1,9)))
            self.assertEqual(db.restore_test(backup)['integrity'],'ok')
            with closing(db.connect()) as conn:
                self.assertEqual([tuple(r) for r in conn.execute('SELECT * FROM companies')],before)
            self.assertEqual(db.applied_migration_versions(db.DB_PATH),set(range(1,10)))


class PlanningUITests(unittest.TestCase):
    run_ui=test_stage61a.Stage61aTests.run_ui

    def test_deliverable_reset_edit_and_acceptance_display(self):
        self.run_ui('''
from services.business_service import save_business_record
from services.acceptance_service import document_acceptance
e=save_business_record('engagements',dict(track_id=track,title='TEST Samlet opgave',status='I gang'))
p=save_business_record('proposals',dict(track_id=track,title='TEST Accepteret',version=1,status='Accepteret'))
document_acceptance(p,dict(acceptance_date='2026-10-24',acceptance_method='E-mail',document_reference='TEST Accept.pdf'))
app=AppTest.from_file('app.py')
app.session_state['page']='Forretning'
app.session_state['business_track_id']=track
app.session_state['business_section']='Kundeopgaver'
app.run(timeout=30)
def fresh(kind,label):
    return next(x for x in getattr(app,kind) if x.label==label and str(x.key).startswith(f'deliverable_{e}_new_'))
for title in ['TEST Leverance A','TEST Leverance B']:
    fresh('text_input','Leverancetitel').set_value(title)
    fresh('text_area','Beskrivelse').set_value('TEST Beskrivelse')
    fresh('date_input','Leverancedeadline').set_value(__import__('datetime').date(2026,10,28))
    fresh('selectbox','Prioritet').select('Høj')
    next(x for x in app.button if x.label=='Gem leverance' and '_new_' in x.key).click().run()
    assert not len(app.exception),list(app.exception)
    assert fresh('text_input','Leverancetitel').value==''
    assert fresh('text_area','Beskrivelse').value==''
    assert fresh('date_input','Leverancedeadline').value is None
    assert fresh('selectbox','Prioritet').value=='Middel'
rows=conn.execute('SELECT * FROM deliverables ORDER BY id').fetchall()
assert [r['title'] for r in rows]==['TEST Leverance A','TEST Leverance B']
assert any(x.value=='TEST Leverance A' for x in app.text_input)
app=AppTest.from_file('app.py')
app.session_state['page']='Forretning'
app.session_state['business_track_id']=track
app.session_state['business_section']='Tilbud'
app.run(timeout=30)
assert any('TEST Accept.pdf' in x.value for x in app.markdown),[x.value for x in app.markdown]
assert field(app,'text_input','Reference til acceptdokument').value=='TEST Accept.pdf'
field(app,'text_area','Kort acceptnote').set_value('TEST Suppleret i UI')
submit(app,'Gem acceptdokumentation')
assert conn.execute('SELECT COUNT(*) FROM proposal_acceptances WHERE proposal_id=?',(p,)).fetchone()[0]==2
assert any('TEST Suppleret i UI' in x.value for x in app.markdown)
assert not len(app.exception),list(app.exception)
conn.close()
''')

    def test_week_plan_crud_reset_navigation_and_overload(self):
        self.run_ui('''
from services.business_service import save_business_record
from services.planning_service import local_today
e=save_business_record('engagements',dict(track_id=track,title='TEST Opgave',status='I gang'))
d=save_business_record('deliverables',dict(engagement_id=e,title='TEST Leverance',status='I gang',due_date=local_today().isoformat()))
app=AppTest.from_file('app.py').run(timeout=30)
app.radio(key='dashboard_view').set_value('Ugeplan').run()
assert not len(app.exception),list(app.exception)
app.button(key='plan_new').click().run()
assert field(app,'selectbox','Kundeopgave eller leverance').value is None
field(app,'selectbox','Kundeopgave eller leverance').select((e,d))
field(app,'number_input','Planlagte timer').set_value(9.0)
submit(app,'Gem arbejdsblok')
assert any('Arbejdsblokken er gemt' in x.value for x in app.success)
assert len(app.warning)
from datetime import timedelta
weekend=local_today()+timedelta(days=5-local_today().weekday())
app.date_input(key='capacity_day').set_value(weekend).run()
assert field(app,'number_input','Disponible timer').value==0.0
field(app,'number_input','Disponible timer').set_value(4.0)
submit(app,'Gem dagskapacitet')
assert conn.execute('SELECT capacity_minutes FROM daily_capacity WHERE work_date=?',(weekend.isoformat(),)).fetchone()[0]==240
block=conn.execute('SELECT id FROM work_blocks').fetchone()[0]
app.button(key='plan_new').click().run()
assert field(app,'text_input','Kort beskrivelse').value==''
assert field(app,'number_input','Planlagte timer').value==1.0
field(app,'button','Annuller').click().run()
app.button(key=f'plan_edit_{block}').click().run()
field(app,'text_input','Kort beskrivelse').set_value('TEST Rettet')
field(app,'number_input','Planlagte timer').set_value(2.0)
submit(app,'Gem arbejdsblok')
assert conn.execute('SELECT description FROM work_blocks').fetchone()[0]=='TEST Rettet'
app.button(key=f'plan_edit_{block}').click().run()
field(app,'checkbox','Bekræft sletning af arbejdsblokken').check().run()
next(x for x in app.button if x.label=='Slet arbejdsblok').click().run()
assert conn.execute('SELECT COUNT(*) FROM work_blocks').fetchone()[0]==0
assert conn.execute('SELECT COUNT(*) FROM deliverables').fetchone()[0]==1
old=app.session_state['planning_week_picker']
field(app,'button','Næste uge').click().run()
assert (app.session_state['planning_week_picker']-old).days==7
field(app,'button','Forrige uge').click().run()
assert app.session_state['planning_week_picker']==old
before=list(conn.iterdump())
app.run()
assert list(conn.iterdump())==before
conn.close()
''')
