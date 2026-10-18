import sqlite3
import tempfile
import unittest
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import db

TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / ".test-tmp"


def utc_now_iso():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


@contextmanager
def isolated_database():
    TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="frank-monitor-test-", dir=TEST_TEMP_ROOT
    ) as temp_dir:
        data_dir = Path(temp_dir)
        production_dir = data_dir / "production-must-not-be-used"
        with (
            patch.object(db, "APP_MODE", "test"),
            patch.object(db, "DATA_DIR", data_dir),
            patch.object(db, "PRODUCTION_DATA_DIR", production_dir),
            patch.object(db, "DB_PATH", data_dir / "monitor.db"),
            patch.object(db, "UPLOAD_DIR", data_dir / "UploadedDocuments"),
        ):
            yield data_dir


class DatabaseFoundationTests(unittest.TestCase):
    def test_fresh_database_applies_all_migrations_and_passes_integrity_checks(self):
        with isolated_database() as data_dir:
            db.init_db()

            self.assertEqual(db.applied_migration_versions(db.DB_PATH), {1, 2, 3, 4, 5, 6, 7})
            result = db.verify_database(db.DB_PATH)
            self.assertEqual(result["integrity"], "ok")
            self.assertEqual(result["foreign_key_violations"], 0)
            self.assertIn("companies", result["tables"])
            self.assertIn("followups", result["tables"])
            self.assertIn("commercial_tracks", result["tables"])
            self.assertIn("proposals", result["tables"])
            self.assertIn("engagements", result["tables"])
            self.assertIn("deliverables", result["tables"])
            self.assertIn("meeting_tracks", result["tables"])
            self.assertFalse(list((data_dir / "Backups").glob("*pre_migration*")))

    def test_existing_database_is_backed_up_before_migration_and_keeps_data(self):
        with isolated_database() as data_dir:
            data_dir.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(db.DB_PATH)
            conn.execute(
                """CREATE TABLE companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    category TEXT DEFAULT '',
                    country TEXT DEFAULT 'Danmark',
                    priority TEXT DEFAULT 'Middel',
                    website TEXT DEFAULT '',
                    linkedin TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                "INSERT INTO companies (name, created_at) VALUES (?, ?)",
                ("Bevaret aktør", utc_now_iso()),
            )
            conn.commit()
            conn.close()

            db.init_db()

            backups = list((data_dir / "Backups").glob("monitor_pre_migration_*.db"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(db.verify_database(backups[0])["integrity"], "ok")
            with closing(db.connect()) as migrated:
                row = migrated.execute(
                    "SELECT name, actor_type, status FROM companies WHERE name=?",
                    ("Bevaret aktør",),
                ).fetchone()
                self.assertEqual(tuple(row), ("Bevaret aktør", "Life science-virksomhed", "Aktiv"))
            self.assertEqual(db.applied_migration_versions(db.DB_PATH), {1, 2, 3, 4, 5, 6, 7})

    def test_backup_can_be_restored_and_verified_without_touching_source(self):
        with isolated_database():
            db.init_db()
            before = db.verify_database(db.DB_PATH)["row_counts"]
            backup_path = db.create_backup("test")
            restored = db.restore_test(backup_path)

            self.assertEqual(restored["integrity"], "ok")
            self.assertEqual(restored["foreign_key_violations"], 0)
            self.assertEqual(restored["row_counts"], before)
            self.assertTrue(db.DB_PATH.exists())

    def test_actor_meeting_and_followup_workflow_preserves_relations(self):
        with isolated_database():
            db.init_db()
            now = utc_now_iso()
            with closing(db.connect()) as conn:
                actor_id = conn.execute(
                    "INSERT INTO companies (name, actor_type, created_at) VALUES (?, ?, ?)",
                    ("Testaktør", "Brancheforening", now),
                ).lastrowid
                contact_id = conn.execute(
                    """INSERT INTO contacts
                       (company_id, name, role, phone, email, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (actor_id, "Testkontakt", "Direktør", "12345678", "test@example.com", now),
                ).lastrowid
                meeting_id = conn.execute(
                    """INSERT INTO meetings
                       (company_id, title, meeting_date, raw_text, uploaded_filename, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (actor_id, "Testmøde", "2026-10-17", "Testreferat", "referat.docx", now),
                ).lastrowid
                document_id = conn.execute(
                    """INSERT INTO uploaded_documents
                       (company_id, meeting_id, original_filename, stored_path, extracted_text, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (actor_id, meeting_id, "referat.docx", "test/referat.docx", "Testreferat", now),
                ).lastrowid
                briefing_id = conn.execute(
                    """INSERT INTO briefings
                       (company_id, meeting_id, title, briefing_text, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (actor_id, meeting_id, "Testbriefing", "Lokal briefing", now),
                ).lastrowid
                followup_id = conn.execute(
                    """INSERT INTO followups
                       (company_id, title, followup_type, status, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (actor_id, "Testopfølgning", "Mødeopfølgning", "Ny", now),
                ).lastrowid
                conn.commit()

                meeting_company = conn.execute(
                    "SELECT company_id FROM meetings WHERE id=?", (meeting_id,)
                ).fetchone()[0]
                followup_company = conn.execute(
                    "SELECT company_id FROM followups WHERE id=?", (followup_id,)
                ).fetchone()[0]
                self.assertEqual(meeting_company, actor_id)
                self.assertEqual(followup_company, actor_id)
                self.assertEqual(
                    conn.execute(
                        "SELECT company_id FROM contacts WHERE id=?", (contact_id,)
                    ).fetchone()[0],
                    actor_id,
                )
                self.assertEqual(
                    conn.execute(
                        "SELECT meeting_id FROM uploaded_documents WHERE id=?", (document_id,)
                    ).fetchone()[0],
                    meeting_id,
                )
                self.assertEqual(
                    conn.execute(
                        "SELECT meeting_id FROM briefings WHERE id=?", (briefing_id,)
                    ).fetchone()[0],
                    meeting_id,
                )
                self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])


if __name__ == "__main__":
    unittest.main()
