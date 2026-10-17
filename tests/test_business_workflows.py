import unittest
from contextlib import closing

import db
from services.business_service import (
    create_engagement_from_proposal,
    set_deliverable_followups,
    set_track_followups,
    set_track_meetings,
)
from tests.test_db_foundation import isolated_database, utc_now_iso


class BusinessWorkflowTests(unittest.TestCase):
    def test_illustrative_nomeco_glostrup_and_tmj_scenarios(self):
        with isolated_database():
            db.init_db()
            now = utc_now_iso()
            with closing(db.connect()) as conn:
                nomeco_id = conn.execute(
                    "INSERT INTO companies (name, created_at) VALUES (?, ?)",
                    ("TEST Nomeco", now),
                ).lastrowid
                glostrup_id = conn.execute(
                    "INSERT INTO companies (name, created_at) VALUES (?, ?)",
                    ("TEST Glostrup Apotek", now),
                ).lastrowid
                tmj_id = conn.execute(
                    "INSERT INTO companies (name, created_at) VALUES (?, ?)",
                    ("TEST TMJ", now),
                ).lastrowid

                nomeco_track = conn.execute(
                    """INSERT INTO commercial_tracks
                       (company_id, title, need_description, status, created_at, updated_at)
                       VALUES (?, ?, ?, 'Lukket', ?, ?)""",
                    (nomeco_id, "Afsluttet rådgivning", "Historisk testopgave", now, now),
                ).lastrowid
                nomeco_engagement = conn.execute(
                    """INSERT INTO engagements
                       (track_id, title, status, fee_model, agreed_fee_ex_vat,
                        completed_at, future_collaboration_note, created_at, updated_at)
                       VALUES (?, ?, 'Afsluttet', 'Fast pris', ?, ?, ?, ?, ?)""",
                    (
                        nomeco_track,
                        "Gennemført rådgivningsopgave",
                        25000,
                        "2026-09-30",
                        "Muligt nyt samarbejde, men ingen automatisk mulighed",
                        now,
                        now,
                    ),
                ).lastrowid
                nomeco_deliverable = conn.execute(
                    """INSERT INTO deliverables
                       (engagement_id, title, due_date, status, created_at, updated_at)
                       VALUES (?, 'Afsluttende leverance', '2026-09-30', 'Leveret', ?, ?)""",
                    (nomeco_engagement, now, now),
                ).lastrowid
                nomeco_followup = conn.execute(
                    """INSERT INTO followups
                       (company_id, title, status, created_at)
                       VALUES (?, 'Arkivér leverance', 'Lukket', ?)""",
                    (nomeco_id, now),
                ).lastrowid

                glostrup_track_1 = conn.execute(
                    """INSERT INTO commercial_tracks
                       (company_id, title, status, created_at, updated_at)
                       VALUES (?, ?, 'Afventer', ?, ?)""",
                    (glostrup_id, "Rådgivningsbehov A", now, now),
                ).lastrowid
                glostrup_track_2 = conn.execute(
                    """INSERT INTO commercial_tracks
                       (company_id, title, status, created_at, updated_at)
                       VALUES (?, ?, 'Afventer', ?, ?)""",
                    (glostrup_id, "Rådgivningsbehov B", now, now),
                ).lastrowid
                proposal_1 = conn.execute(
                    """INSERT INTO proposals
                       (track_id, title, version, scope, fee_model, offered_fee_ex_vat,
                        fee_note, status, created_at, updated_at)
                       VALUES (?, ?, 1, ?, 'Fast pris', ?, ?, 'Afventer', ?, ?)""",
                    (
                        glostrup_track_1,
                        "Tilbud A",
                        "Afgrænset rådgivning",
                        30000,
                        "Ekskl. eventuelle rejseudgifter",
                        now,
                        now,
                    ),
                ).lastrowid
                conn.execute(
                    """INSERT INTO proposals
                       (track_id, title, version, fee_model, offered_fee_ex_vat,
                        status, created_at, updated_at)
                       VALUES (?, ?, 2, 'Timepris', ?, 'Sendt', ?, ?)""",
                    (glostrup_track_1, "Tilbud A - alternativ", 1800, now, now),
                )
                conn.execute(
                    """INSERT INTO proposals
                       (track_id, title, version, status, created_at, updated_at)
                       VALUES (?, ?, 1, 'Afventer', ?, ?)""",
                    (glostrup_track_2, "Tilbud B", now, now),
                )

                shared_meeting = conn.execute(
                    """INSERT INTO meetings
                       (company_id, title, meeting_date, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (glostrup_id, "Fælles tilbudsmøde", "2026-11-01", now),
                ).lastrowid
                followup_id = conn.execute(
                    """INSERT INTO followups
                       (company_id, title, status, created_at)
                       VALUES (?, ?, 'Ny', ?)""",
                    (glostrup_id, "Følg op på tilbud A", now),
                ).lastrowid
                conn.execute(
                    """INSERT INTO meetings
                       (company_id, title, meeting_date, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (tmj_id, "Kommende indledende møde", "2026-12-01", now),
                )
                conn.commit()

            set_track_meetings(glostrup_track_1, [shared_meeting])
            set_track_meetings(glostrup_track_2, [shared_meeting])
            set_track_followups(glostrup_track_1, [followup_id])
            set_deliverable_followups(nomeco_deliverable, [nomeco_followup])
            converted_engagement = create_engagement_from_proposal(
                proposal_1,
                "Accepteret rådgivningsopgave A",
                "Afgrænset rådgivning",
                "Planlagt",
                "2026-11-10",
                "2026-12-15",
                "Fast pris",
                28000,
                "Aftalt lavere end tilbudt",
            )

            with closing(db.connect()) as conn:
                self.assertEqual(
                    conn.execute(
                        "SELECT COUNT(*) FROM commercial_tracks WHERE company_id=?",
                        (glostrup_id,),
                    ).fetchone()[0],
                    2,
                )
                self.assertEqual(
                    conn.execute(
                        "SELECT COUNT(*) FROM proposals WHERE track_id=?",
                        (glostrup_track_1,),
                    ).fetchone()[0],
                    2,
                )
                self.assertEqual(
                    conn.execute(
                        "SELECT COUNT(*) FROM meeting_tracks WHERE meeting_id=?",
                        (shared_meeting,),
                    ).fetchone()[0],
                    2,
                )
                self.assertEqual(
                    conn.execute(
                        "SELECT commercial_track_id FROM followups WHERE id=?", (followup_id,)
                    ).fetchone()[0],
                    glostrup_track_1,
                )
                converted = conn.execute(
                    """SELECT accepted_proposal_id, agreed_fee_ex_vat, fee_model
                       FROM engagements WHERE id=?""",
                    (converted_engagement,),
                ).fetchone()
                self.assertEqual(converted["accepted_proposal_id"], proposal_1)
                self.assertEqual(float(converted["agreed_fee_ex_vat"]), 28000.0)
                self.assertEqual(converted["fee_model"], "Fast pris")
                self.assertEqual(
                    conn.execute("SELECT status FROM proposals WHERE id=?", (proposal_1,)).fetchone()[0],
                    "Accepteret",
                )
                self.assertEqual(
                    conn.execute(
                        "SELECT accepted_proposal_id FROM engagements WHERE id=?",
                        (nomeco_engagement,),
                    ).fetchone()[0],
                    None,
                )
                linked_delivery = conn.execute(
                    "SELECT commercial_track_id, deliverable_id FROM followups WHERE id=?",
                    (nomeco_followup,),
                ).fetchone()
                self.assertEqual(tuple(linked_delivery), (nomeco_track, nomeco_deliverable))
                self.assertEqual(
                    conn.execute(
                        "SELECT COUNT(*) FROM commercial_tracks WHERE company_id=?", (tmj_id,)
                    ).fetchone()[0],
                    0,
                )
                self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_cross_actor_meeting_and_followup_links_are_rejected(self):
        with isolated_database():
            db.init_db()
            now = utc_now_iso()
            with closing(db.connect()) as conn:
                actor_a = conn.execute(
                    "INSERT INTO companies (name, created_at) VALUES ('TEST Aktør A', ?)", (now,)
                ).lastrowid
                actor_b = conn.execute(
                    "INSERT INTO companies (name, created_at) VALUES ('TEST Aktør B', ?)", (now,)
                ).lastrowid
                track = conn.execute(
                    """INSERT INTO commercial_tracks
                       (company_id, title, created_at, updated_at) VALUES (?, 'Testforløb', ?, ?)""",
                    (actor_a, now, now),
                ).lastrowid
                meeting = conn.execute(
                    "INSERT INTO meetings (company_id, title, created_at) VALUES (?, 'Forkert møde', ?)",
                    (actor_b, now),
                ).lastrowid
                followup = conn.execute(
                    "INSERT INTO followups (company_id, title, created_at) VALUES (?, 'Forkert opfølgning', ?)",
                    (actor_b, now),
                ).lastrowid
                conn.commit()
            with self.assertRaises(ValueError):
                set_track_meetings(track, [meeting])
            with self.assertRaises(ValueError):
                set_track_followups(track, [followup])


if __name__ == "__main__":
    unittest.main()
