import json
import sqlite3
import unittest
from contextlib import closing
from unittest.mock import patch

import db
from services.business_service import (save_business_record, create_engagement_from_proposal,
    record_amendment, set_track_followups, set_deliverable_followups)
from services.business_values import parse_danish_number, number_text, fee_text, parse_date, iso_date
from tests.test_db_foundation import isolated_database


class Stage4Tests(unittest.TestCase):
    def setUp(self):
        self.isolation = isolated_database()
        self.data_dir = self.isolation.__enter__()
        db.init_db()
        with closing(db.connect()) as conn:
            self.actor = conn.execute("INSERT INTO companies(name,created_at) VALUES('TEST Etape 4',?)", (db.utc_now_iso(),)).lastrowid
            conn.commit()
        self.track = save_business_record('commercial_tracks', {'company_id':self.actor, 'title':'Testforløb'})

    def tearDown(self):
        self.isolation.__exit__(None, None, None)

    def proposal(self, **extra):
        values = dict(track_id=self.track, title='Testtilbud', version=1, fee_model='Fast pris',
                      offered_fee_ex_vat=None, status='Kladde')
        values.update(extra)
        return save_business_record('proposals', values)

    def row(self, table, record_id):
        with closing(db.connect()) as conn:
            return dict(conn.execute(f'SELECT * FROM {table} WHERE id=?', (record_id,)).fetchone())

    def convert(self, pid, **extra):
        return create_engagement_from_proposal(pid, 'Testopgave', 'Oprindelig beskrivelse',
            'Planlagt', '', '', 'Fast pris', 25000, 'Vilkår', **extra)

    def test_optional_zero_and_positive_fees(self):
        for version, (text, expected) in enumerate([('', None), ('0', 0), ('12.500,50',12500.5)], 1):
            pid = self.proposal(version=version, offered_fee_ex_vat=parse_danish_number(text))
            self.assertEqual(self.row('proposals',pid)['offered_fee_ex_vat'], expected)
        self.assertEqual(fee_text(None), 'Honorar ikke registreret')
        self.assertIn('0,00 kr.', fee_text(0))
        self.assertEqual(number_text(12500.5), '12.500,50')

    def test_reject_invalid_danish_numbers(self):
        for text in ['-1', '12.50', '12,333', 'NaN', '1e4', 'abc']:
            with self.assertRaises(ValueError, msg=text):
                parse_danish_number(text)

    def test_hourly_retainer_and_limits(self):
        pid = self.proposal(fee_model='Timepris', offered_fee_ex_vat=1800, max_hours=15, fee_cap_ex_vat=25000)
        row = self.row('proposals',pid)
        self.assertEqual((row['max_hours'],row['fee_cap_ex_vat']), (15,25000))
        self.assertIn('kr./time', fee_text(row['offered_fee_ex_vat'], row['fee_model']))
        pid2 = self.proposal(version=2,fee_model='Klippekort / retainer',offered_fee_ex_vat=30000,included_hours=20)
        self.assertEqual(self.row('proposals',pid2)['included_hours'],20)
        pid3 = self.proposal(version=3, fee_model='Endnu ikke aftalt')
        self.assertIsNone(self.row('proposals',pid3)['offered_fee_ex_vat'])

    def test_draft_and_sent_editable_accept_requires_correction(self):
        pid = self.proposal()
        values = dict(track_id=self.track,title='Tilrettet',version=1,status='Sendt',offered_fee_ex_vat=20000)
        save_business_record('proposals',values,pid)
        values['status']='Accepteret'
        save_business_record('proposals',values,pid)
        values['offered_fee_ex_vat']=21000
        with self.assertRaises(ValueError):
            save_business_record('proposals',values,pid)
        save_business_record('proposals',values,pid,'Rettet registreringsfejl')
        with closing(db.connect()) as conn:
            log = conn.execute('SELECT * FROM proposal_changes WHERE proposal_id=?',(pid,)).fetchone()
            self.assertEqual(json.loads(log['previous_values'])['offered_fee_ex_vat'],20000)
            self.assertEqual(json.loads(log['new_values'])['offered_fee_ex_vat'],21000)
            self.assertTrue(log['changed_at'])
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE proposals SET scope='Overført uden log', updated_at='unlogged' WHERE id=?",(pid,))
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE proposals SET scope='Genbrug af gammel log' WHERE id=?",(pid,))

    def test_conversion_duplicate_and_original_agreement(self):
        pid = self.proposal(offered_fee_ex_vat=30000)
        eid = self.convert(pid,max_hours=12,fee_cap_ex_vat=25000)
        with self.assertRaises(ValueError):
            self.convert(pid)
        before = self.row('proposals',pid)
        save_business_record('engagements',dict(title='Udvidet opgave',description='Ændret beskrivelse',
            agreed_fee_ex_vat=28000, actual_hours=17.5, reuse_potential='Ja', reuse_notes='Genbrugbar metode'),eid)
        self.assertEqual(self.row('proposals',pid),before)
        row = self.row('engagements',eid)
        original = json.loads(row['original_agreement'])
        self.assertEqual(original['description'],'Oprindelig beskrivelse')
        self.assertEqual(original['agreed_fee_ex_vat'],25000)
        self.assertEqual(row['actual_hours'],17.5)
        self.assertEqual(row['reuse_potential'],'Ja')

    def test_amendment_and_direct_engagement_snapshot(self):
        eid = save_business_record('engagements',dict(track_id=self.track,title='Direkte aftale',agreed_fee_ex_vat=5000))
        record_amendment(eid,'2026-10-18','Udvidet leverance','Mail 18-10-2026',6000)
        row = self.row('engagements',eid)
        self.assertEqual(row['agreed_fee_ex_vat'],6000)
        self.assertEqual(json.loads(row['original_agreement'])['agreed_fee_ex_vat'],5000)
        delivery = save_business_record('deliverables',dict(engagement_id=eid,title='Testleverance'))
        with closing(db.connect()) as conn:
            followup = conn.execute('INSERT INTO followups(company_id,title,created_at) VALUES(?,?,?)',
                (self.actor,'Leveranceopfølgning',db.utc_now_iso())).lastrowid
            conn.commit()
        set_deliverable_followups(delivery,[followup])
        set_track_followups(self.track,[followup])
        with closing(db.connect()) as conn:
            self.assertEqual(conn.execute('SELECT deliverable_id FROM followups WHERE id=?',(followup,)).fetchone()[0], delivery)
        with closing(db.connect()) as conn:
            change = conn.execute('SELECT * FROM engagement_amendments WHERE engagement_id=?',(eid,)).fetchone()
            self.assertEqual((change['previous_fee'],change['new_fee']),(5000,6000))
            self.assertEqual(change['acceptance_reference'],'Mail 18-10-2026')
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_optional_and_historical_dates(self):
        self.assertIsNone(parse_date(''))
        self.assertEqual(iso_date(None),'')
        self.assertEqual(iso_date(parse_date('1995-05-20')),'1995-05-20')
        pid = self.proposal(sent_date='', valid_until='')
        self.assertEqual(self.row('proposals',pid)['valid_until'],'')

    def test_production_upgrade_stops_before_any_writes(self):
        from runtime_config import RuntimeConfigurationError
        with (patch.object(db, 'APP_MODE', 'production'),
              patch.object(db, 'PRODUCTION_DATA_DIR', self.data_dir),
              patch.object(db, 'pending_migrations', return_value=[db.MIGRATIONS[-1]]),
              patch.object(db, 'ensure_data_dir') as ensure):
            with self.assertRaises(RuntimeConfigurationError):
                db.init_db()
            ensure.assert_not_called()

    def test_migration_preserves_stage3_data_and_backup_rollback(self):
        # Build a version-4 database, then run the normal upgrade path.
        legacy = self.data_dir / 'legacy.db'
        with closing(db.connect(legacy)) as conn:
            conn.execute(db.MIGRATION_TABLE_SQL)
            for version,name,migration in db.MIGRATIONS[:4]:
                migration(conn)
                conn.execute('INSERT INTO schema_migrations VALUES(?,?,?)',(version,name,db.utc_now_iso()))
            actor = conn.execute("INSERT INTO companies(name,created_at) VALUES('Bevaret',?)",(db.utc_now_iso(),)).lastrowid
            track = conn.execute("INSERT INTO commercial_tracks(company_id,title,created_at) VALUES(?,'Bevaret forløb',?)",(actor,db.utc_now_iso())).lastrowid
            conn.execute("INSERT INTO proposals(track_id,title,status,offered_fee_ex_vat,created_at) VALUES(?,'Bevaret nul','Accepteret',0,?)",(track,db.utc_now_iso()))
            conn.commit()
        before = db.verify_database(legacy)['row_counts']
        with patch.object(db,'DB_PATH',legacy):
            db.init_db()
        backups = list((self.data_dir/'Backups').glob('*pre_migration*'))
        self.assertEqual(len(backups),1)
        self.assertEqual(db.verify_database(backups[0])['row_counts'],before)
        self.assertEqual(db.restore_test(backups[0])['row_counts'],before)
        with closing(db.connect(legacy)) as conn:
            self.assertEqual(conn.execute('SELECT offered_fee_ex_vat FROM proposals').fetchone()[0],0)
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(),[])


if __name__ == '__main__':
    unittest.main()
