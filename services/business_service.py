from contextlib import closing

from db import connect, utc_now_iso


def next_proposal_version(track_id):
    with closing(connect()) as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM proposals WHERE track_id=?",
            (track_id,),
        ).fetchone()
        return int(row[0])


def create_engagement_from_proposal(
    proposal_id,
    title,
    description,
    status,
    start_date,
    target_end_date,
    fee_model,
    agreed_fee_ex_vat,
    fee_note,
):
    """Create an engagement only after the user submits the explicit conversion form."""
    now = utc_now_iso()
    with closing(connect()) as conn:
        proposal = conn.execute(
            """SELECT p.*, t.company_id
               FROM proposals p
               JOIN commercial_tracks t ON t.id=p.track_id
               WHERE p.id=?""",
            (proposal_id,),
        ).fetchone()
        if proposal is None:
            raise ValueError("Tilbuddet findes ikke.")
        existing = conn.execute(
            "SELECT id FROM engagements WHERE accepted_proposal_id=?",
            (proposal_id,),
        ).fetchone()
        if existing:
            raise ValueError("Tilbuddet er allerede knyttet til en kundeopgave.")
        try:
            conn.execute("BEGIN")
            conn.execute(
                "UPDATE proposals SET status='Accepteret', updated_at=? WHERE id=?",
                (now, proposal_id),
            )
            cursor = conn.execute(
                """INSERT INTO engagements
                   (track_id, accepted_proposal_id, title, description, fee_model,
                    agreed_fee_ex_vat, fee_note, status, start_date, target_end_date,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    proposal["track_id"],
                    proposal_id,
                    title,
                    description,
                    fee_model,
                    agreed_fee_ex_vat,
                    fee_note,
                    status,
                    start_date,
                    target_end_date,
                    now,
                    now,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)
        except Exception:
            conn.rollback()
            raise


def set_track_meetings(track_id, meeting_ids):
    """Replace meeting links while preventing links across actors."""
    selected_ids = sorted({int(value) for value in meeting_ids})
    now = utc_now_iso()
    with closing(connect()) as conn:
        track = conn.execute(
            "SELECT company_id FROM commercial_tracks WHERE id=?", (track_id,)
        ).fetchone()
        if track is None:
            raise ValueError("Forretningsforløbet findes ikke.")
        if selected_ids:
            placeholders = ",".join("?" for _ in selected_ids)
            rows = conn.execute(
                f"SELECT id, company_id FROM meetings WHERE id IN ({placeholders})",
                selected_ids,
            ).fetchall()
            if len(rows) != len(selected_ids) or any(
                row["company_id"] != track["company_id"] for row in rows
            ):
                raise ValueError("Møder kan kun knyttes til forløb hos samme aktør.")
        try:
            conn.execute("BEGIN")
            conn.execute("DELETE FROM meeting_tracks WHERE track_id=?", (track_id,))
            conn.executemany(
                "INSERT INTO meeting_tracks (meeting_id, track_id, created_at) VALUES (?, ?, ?)",
                [(meeting_id, track_id, now) for meeting_id in selected_ids],
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def set_track_followups(track_id, followup_ids):
    """Link existing follow-ups to one track without copying their content."""
    selected_ids = sorted({int(value) for value in followup_ids})
    with closing(connect()) as conn:
        track = conn.execute(
            "SELECT company_id FROM commercial_tracks WHERE id=?", (track_id,)
        ).fetchone()
        if track is None:
            raise ValueError("Forretningsforløbet findes ikke.")
        if selected_ids:
            placeholders = ",".join("?" for _ in selected_ids)
            rows = conn.execute(
                f"SELECT id, company_id FROM followups WHERE id IN ({placeholders})",
                selected_ids,
            ).fetchall()
            if len(rows) != len(selected_ids) or any(
                row["company_id"] != track["company_id"] for row in rows
            ):
                raise ValueError("Opfølgninger kan kun knyttes til forløb hos samme aktør.")
        try:
            conn.execute("BEGIN")
            conn.execute(
                "UPDATE followups SET commercial_track_id=NULL WHERE commercial_track_id=?",
                (track_id,),
            )
            if selected_ids:
                placeholders = ",".join("?" for _ in selected_ids)
                conn.execute(
                    f"UPDATE followups SET commercial_track_id=? WHERE id IN ({placeholders})",
                    (track_id, *selected_ids),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def set_deliverable_followups(deliverable_id, followup_ids):
    """Link existing follow-ups to a deliverable and its existing track."""
    selected_ids = sorted({int(value) for value in followup_ids})
    with closing(connect()) as conn:
        context = conn.execute(
            """SELECT e.track_id, t.company_id
               FROM deliverables d
               JOIN engagements e ON e.id=d.engagement_id
               JOIN commercial_tracks t ON t.id=e.track_id
               WHERE d.id=?""",
            (deliverable_id,),
        ).fetchone()
        if context is None:
            raise ValueError("Leverancen findes ikke.")
        if selected_ids:
            placeholders = ",".join("?" for _ in selected_ids)
            rows = conn.execute(
                f"SELECT id, company_id FROM followups WHERE id IN ({placeholders})",
                selected_ids,
            ).fetchall()
            if len(rows) != len(selected_ids) or any(
                row["company_id"] != context["company_id"] for row in rows
            ):
                raise ValueError("Opfølgninger kan kun knyttes til leverancer hos samme aktør.")
        try:
            conn.execute("BEGIN")
            conn.execute(
                "UPDATE followups SET deliverable_id=NULL WHERE deliverable_id=?",
                (deliverable_id,),
            )
            if selected_ids:
                placeholders = ",".join("?" for _ in selected_ids)
                conn.execute(
                    f"""UPDATE followups
                        SET deliverable_id=?, commercial_track_id=?
                        WHERE id IN ({placeholders})""",
                    (deliverable_id, context["track_id"], *selected_ids),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
