import json
import unittest
from contextlib import closing
from datetime import date
from unittest.mock import patch

import db
from services.activity_service import build_dashboard, dashboard_data
from services.business_service import (save_business_record, create_engagement_from_proposal,
    record_amendment, accept_amendment, document_legacy_acceptance)
from services.business_values import parse_danish_number, timestamp_text
from tests.test_db_foundation import isolated_database


class ActivityTests(unittest.TestCase):
    def test_dates_counts_and_duplicate_followup(self):
        base=dict(company='TEST Glostrup Apotek',company_id=1,title='Juridisk vurderingsnotat',
                  status='Ikke startet',engagement_status='I gang',track_id=1,engagement_id=1)
        deliveries=[dict(base,id=1,due_date='2026-10-24'),dict(base,id=2,due_date='2026-10-17'),
                    dict(base,id=3,due_date='2026-10-18'),dict(base,id=4,due_date='2026-11-17'),
                    dict(base,id=5,due_date='2026-11-18'),dict(base,id=6,due_date=''),
                    dict(base,id=7,due_date='2026-10-24',status='Leveret'),
                    dict(base,id=8,due_date='2026-10-24',engagement_status='Afsluttet')]
        followups=[dict(id=1,title='Samme deadline',status='Ny',due_date='2026-10-24',deliverable_id=1,next_action=''),
                   dict(id=2,title='Selvstændig handling',status='Ny',due_date='2026-10-24',deliverable_id=1,next_action='Ring til kunden')]
        data=build_dashboard(date(2026,10,18),[],[],deliveries,[],[],followups)
        self.assertEqual(data['overdue'],1)
        self.assertEqual(data['next30'],4)
        self.assertEqual(len(data['activities']),5)
        self.assertEqual(len(data['activities'][1]['related_followups']),0)
        item=next(e for e in data['activities'] if e['kind']=='Leverancefrist' and e['id']==1)
        self.assertEqual(len(item['related_followups']),1)
        self.assertEqual(len(data['groups']['Åbne leverancer']),6)
        self.assertEqual(len(data['rest_deliveries']),1)

    def test_decision_is_not_binding_and_old_meetings_not_overdue(self):
        track=dict(id=1,title='Forventning',status='Åben',expected_decision_date='2026-10-17')
        meetings=[dict(id=1,title='Gammelt møde',meeting_date='2026-10-01'),
                  dict(id=2,title='Nyt møde',meeting_date='2026-10-24')]
        data=build_dashboard(date(2026,10,18),[track],[],[],[],meetings,[])
        self.assertEqual(len(data['activities']),2)
        self.assertFalse(data['activities'][0]['binding'])
        self.assertEqual(data['activities'][1]['kind'],'Møde')

    def test_currency_forms_and_hour_separation(self):
        self.assertEqual(timestamp_text('2026-10-17T23:17:00'),'18-10-2026 kl. 01:17')
        for text in ['25000','25.000','25.000,00','25.000 kr.','25.000 kr','25.000 DKK']:
            self.assertEqual(parse_danish_number(text,allow_currency=True),25000)
        self.assertIsNone(parse_danish_number('',allow_currency=True))
        self.assertEqual(parse_danish_number('0 kr.',allow_currency=True),0)
        for text in ['25.00','25,000','kr.','25.000 kr. ekstra','-10 kr.']:
            with self.assertRaises(ValueError,msg=text):
                parse_danish_number(text,allow_currency=True)
        with self.assertRaises(ValueError):
            parse_danish_number('10 kr.')


class AgreementTests(unittest.TestCase):
    def setUp(self):
        self.context=isolated_database()
        self.folder=self.context.__enter__()
        db.init_db()
        with closing(db.connect()) as conn:
            actor=conn.execute("INSERT INTO companies(name,created_at) VALUES('TEST Glostrup Apotek',?)",(db.utc_now_iso(),)).lastrowid
            conn.commit()
        self.track=save_business_record('commercial_tracks',dict(company_id=actor,title='TEST rådgivning'))

    def tearDown(self):
        self.context.__exit__(None,None,None)

    def row(self,table,record_id):
        with closing(db.connect()) as conn:
            return dict(conn.execute(f'SELECT * FROM {table} WHERE id=?',(record_id,)).fetchone())

    def test_full_fee_chain_proposed_acceptance_and_immutable_original(self):
        pid=save_business_record('proposals',dict(track_id=self.track,title='Tilbud',version=1,
            offered_fee_ex_vat=0,fee_model='Fast pris',status='Kladde'))
        eid=create_engagement_from_proposal(pid,'Direkte aftalt opgave','Omfang','I gang','','','Fast pris',2700,'')
        with patch('services.business_service.utc_now_iso',return_value=self.row('proposals',pid)['updated_at']):
            save_business_record('proposals',dict(title='Tilbud',status='Accepteret',offered_fee_ex_vat=20000),pid,'Registreringsfejl')
        before=self.row('engagements',eid)
        self.assertEqual(before['agreed_fee_ex_vat'],2700)
        self.assertEqual(json.loads(before['accepted_proposal_snapshot'])['offered_fee_ex_vat'],0)
        amendment=record_amendment(eid,'2026-10-18','Udvidet omfang','Mail fra kunden',25000)
        self.assertEqual(self.row('engagements',eid)['agreed_fee_ex_vat'],2700)
        accept_amendment(amendment,'Mundtlig aftale på møde 18-10')
        after=self.row('engagements',eid)
        self.assertEqual(after['agreed_fee_ex_vat'],25000)
        self.assertEqual(json.loads(after['original_agreement'])['agreed_fee_ex_vat'],2700)
        self.assertEqual(self.row('proposals',pid)['offered_fee_ex_vat'],20000)
        self.assertTrue(self.row('engagement_amendments',amendment)['accepted_at'])
        with self.assertRaises(ValueError):
            accept_amendment(amendment)
        with self.assertRaises(ValueError):
            save_business_record('engagements',dict(title='Opgave',agreed_fee_ex_vat=123),eid)

    def test_stale_proposal_and_terms_only_acceptance(self):
        eid=save_business_record('engagements',dict(track_id=self.track,title='Uden tilbud',agreed_fee_ex_vat=1000))
        stale=record_amendment(eid,'','Gammelt forslag','',2000)
        accepted=record_amendment(eid,'','Nye vilkår','',status='Accepteret',terms={'max_hours':10,'fee_cap_ex_vat':5000})
        self.assertEqual(self.row('engagements',eid)['agreed_fee_ex_vat'],1000)
        self.assertEqual(self.row('engagements',eid)['max_hours'],10)
        self.assertEqual(self.row('engagement_amendments',accepted)['acceptance_reference'],'')
        with self.assertRaises(ValueError):
            accept_amendment(stale)
        self.assertEqual(self.row('engagement_amendments',stale)['status'],'Foreslået')

    def test_migration_preserves_legacy_effect_and_rollback(self):
        legacy=self.folder/'stage4.db'
        with closing(db.connect(legacy)) as conn:
            conn.execute(db.MIGRATION_TABLE_SQL)
            for version,name,migration in db.MIGRATIONS[:5]:
                migration(conn)
                conn.execute('INSERT INTO schema_migrations VALUES(?,?,?)',(version,name,db.utc_now_iso()))
            actor=conn.execute("INSERT INTO companies(name,created_at) VALUES('TEST Legacy',?)",(db.utc_now_iso(),)).lastrowid
            track=conn.execute("INSERT INTO commercial_tracks(company_id,title,created_at) VALUES(?,'Forløb',?)",(actor,db.utc_now_iso())).lastrowid
            eid=conn.execute("INSERT INTO engagements(track_id,title,agreed_fee_ex_vat,original_agreement,created_at) VALUES(?,'Opgave',25000,?,?)",(track,json.dumps({'agreed_fee_ex_vat':2700}),db.utc_now_iso())).lastrowid
            aid=conn.execute("INSERT INTO engagement_amendments(engagement_id,description,previous_fee,new_fee,created_at) VALUES(?,'Historisk',2700,25000,?)",(eid,db.utc_now_iso())).lastrowid
            conn.commit()
        counts=db.verify_database(legacy)['row_counts']
        with patch.object(db,'DB_PATH',legacy):
            db.init_db()
            row=self.row('engagements',eid)
            self.assertEqual(row['agreed_fee_ex_vat'],25000)
            self.assertEqual(row['accepted_proposal_snapshot'],'')
            self.assertEqual(self.row('engagement_amendments',aid)['status'],'Historisk registreret')
            document_legacy_acceptance(aid,'Mail fra kunden')
            self.assertEqual(self.row('engagements',eid)['agreed_fee_ex_vat'],25000)
            self.assertEqual(self.row('engagements',eid)['agreement_revision'],0)
            self.assertEqual(self.row('engagement_amendments',aid)['status'],'Historisk dokumenteret')
            self.assertEqual(db.verify_database(legacy)['foreign_key_violations'],0)
            backup=next((self.folder/'Backups').glob('*pre_migration*'))
            self.assertEqual(db.restore_test(backup)['row_counts'],counts)
