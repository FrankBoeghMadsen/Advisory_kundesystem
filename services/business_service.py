from contextlib import closing
import json

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
    max_hours=None,
    fee_cap_ex_vat=None,
    included_hours=None,
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
            conn.execute("BEGIN IMMEDIATE")
            if proposal["status"] != "Accepteret":
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
            conn.execute(
                """UPDATE engagements SET max_hours=?, fee_cap_ex_vat=?, included_hours=?
                   WHERE id=?""",
                (max_hours, fee_cap_ex_vat, included_hours, cursor.lastrowid),
            )
            snapshot = dict(conn.execute("SELECT * FROM engagements WHERE id=?", (cursor.lastrowid,)).fetchone())
            snapshot.pop('original_agreement', None)
            conn.execute("UPDATE engagements SET original_agreement=? WHERE id=?",
                         (json.dumps(snapshot, ensure_ascii=False), cursor.lastrowid))
            conn.commit()
            return int(cursor.lastrowid)
        except Exception:
            conn.rollback()
            raise


EDIT_FIELDS = {
    'proposals': {'track_id', 'title', 'version', 'scope', 'deliverables_summary',
                  'assumptions', 'fee_model', 'offered_fee_ex_vat', 'fee_note', 'status',
                  'sent_date', 'valid_until', 'document_reference', 'max_hours',
                  'fee_cap_ex_vat', 'included_hours'},
    'engagements': {'track_id', 'title', 'description', 'fee_model', 'agreed_fee_ex_vat',
                    'fee_note', 'status', 'start_date', 'target_end_date', 'completed_at',
                    'outcome_notes', 'future_collaboration_note', 'max_hours',
                    'fee_cap_ex_vat', 'included_hours', 'actual_hours', 'reuse_potential', 'reuse_notes'},
    'commercial_tracks': {'company_id', 'primary_contact_id', 'title', 'need_description',
                          'service_area', 'status', 'expected_decision_date', 'close_reason', 'closed_at'},
    'deliverables': {'engagement_id', 'title', 'description', 'due_date', 'priority',
                     'status', 'completed_at', 'responsible_note'},
}


def save_business_record(table, values, record_id=None, correction_reason=''):
    if table not in EDIT_FIELDS or set(values) - EDIT_FIELDS[table]:
        raise ValueError('Ukendte felter.')
    if not str(values.get('title', '')).strip():
        raise ValueError('Titel skal udfyldes.')
    for key in ('offered_fee_ex_vat', 'agreed_fee_ex_vat', 'max_hours', 'fee_cap_ex_vat',
                'included_hours', 'actual_hours'):
        value = values.get(key)
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            raise ValueError('Beløb og timer skal være positive eller tomme.')
    now = utc_now_iso()
    with closing(connect()) as conn:
        try:
            conn.execute('BEGIN IMMEDIATE')
            old = conn.execute(f'SELECT * FROM {table} WHERE id=?', (record_id,)).fetchone() if record_id else None
            if record_id and old is None:
                raise ValueError('Posten findes ikke længere.')
            if table == 'proposals' and old and old['status'] == 'Accepteret':
                if not correction_reason.strip():
                    raise ValueError('Accepterede tilbud kræver en begrundet korrektion.')
                if values.get('status') != 'Accepteret' or values.get('track_id', old['track_id']) != old['track_id']:
                    raise ValueError('En korrektion må ikke ophæve accept eller flytte tilbuddet.')
                changes = {key: value for key, value in values.items() if value != old[key]}
                if changes:
                    conn.execute('''INSERT INTO proposal_changes
                        (proposal_id, changed_at, reason, previous_values, new_values)
                        VALUES (?, ?, ?, ?, ?)''',
                        (record_id, now, correction_reason.strip(),
                         json.dumps({key: old[key] for key in changes}, ensure_ascii=False),
                         json.dumps(changes, ensure_ascii=False)))
                else:
                    return record_id
            saved = dict(values, updated_at=now)
            if old:
                assignments = ', '.join(f'{key}=?' for key in saved)
                conn.execute(f'UPDATE {table} SET {assignments} WHERE id=?', (*saved.values(), record_id))
            else:
                saved['created_at'] = now
                columns = ', '.join(saved)
                placeholders = ', '.join('?' for _ in saved)
                record_id = conn.execute(f'INSERT INTO {table} ({columns}) VALUES ({placeholders})', tuple(saved.values())).lastrowid
                if table == 'engagements':
                    conn.execute('UPDATE engagements SET original_agreement=? WHERE id=?',
                                 (json.dumps(saved, ensure_ascii=False), record_id))
            conn.commit()
            return int(record_id)
        except Exception:
            conn.rollback()
            raise


def record_amendment(engagement_id, amendment_date, description, acceptance_reference, new_fee=None):
    if not description.strip():
        raise ValueError('Beskriv aftaleændringen.')
    with closing(connect()) as conn:
        try:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM engagements WHERE id=?', (engagement_id,)).fetchone()
            if row is None:
                raise ValueError('Kundeopgaven findes ikke.')
            if new_fee is not None and new_fee < 0:
                raise ValueError('Honoraret må ikke være negativt.')
            conn.execute('''INSERT INTO engagement_amendments
                (engagement_id, amendment_date, description, previous_fee, new_fee,
                 acceptance_reference, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (engagement_id, amendment_date, description.strip(), row['agreed_fee_ex_vat'],
                 new_fee, acceptance_reference, utc_now_iso()))
            if new_fee is not None:
                conn.execute('UPDATE engagements SET agreed_fee_ex_vat=?, updated_at=? WHERE id=?',
                             (new_fee, utc_now_iso(), engagement_id))
            conn.commit()
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
            if selected_ids:
                placeholders = ",".join("?" for _ in selected_ids)
                conn.execute(
                    f"""UPDATE followups SET commercial_track_id=NULL, deliverable_id=NULL
                        WHERE commercial_track_id=? AND id NOT IN ({placeholders})""",
                    (track_id, *selected_ids),
                )
                conn.execute(
                    f"""UPDATE followups SET
                        deliverable_id=CASE WHEN commercial_track_id=? THEN deliverable_id ELSE NULL END,
                        commercial_track_id=? WHERE id IN ({placeholders})""",
                    (track_id, track_id, *selected_ids),
                )
            else:
                conn.execute(
                    "UPDATE followups SET commercial_track_id=NULL, deliverable_id=NULL WHERE commercial_track_id=?",
                    (track_id,),
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
