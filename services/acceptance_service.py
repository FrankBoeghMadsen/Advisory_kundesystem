from contextlib import closing
from datetime import date

from db import connect, utc_now_iso

ACCEPTANCE_METHODS=['Ikke angivet','E-mail','Mundtlig','Underskrevet aftale','Andet']


def acceptance_values(values=None):
    values=values or {}
    day=values.get('acceptance_date') or ''
    if day:
        try:
            day=date.fromisoformat(str(day)).isoformat()
        except ValueError as exc:
            raise ValueError('Acceptdato skal være en gyldig dato.') from exc
    method=values.get('acceptance_method') or ''
    if method and method not in ACCEPTANCE_METHODS:
        raise ValueError('Ukendt acceptform.')
    return dict(acceptance_date=day,acceptance_method='' if method=='Ikke angivet' else method,
                document_reference=str(values.get('document_reference') or '').strip(),
                note=str(values.get('note') or '').strip())


def insert_acceptance(conn, proposal_id, values):
    data=acceptance_values(values)
    previous=conn.execute('SELECT * FROM proposal_acceptances WHERE proposal_id=? ORDER BY id DESC LIMIT 1',(proposal_id,)).fetchone()
    if previous:
        stored={key:previous[key] for key in data}
        if not any(data.values()) or data==stored:
            return stored
    if any(data.values()):
        conn.execute('''INSERT INTO proposal_acceptances
            (proposal_id,acceptance_date,acceptance_method,document_reference,note,recorded_at)
            VALUES(?,?,?,?,?,?)''',(proposal_id,*data.values(),utc_now_iso()))
    return data


def document_acceptance(proposal_id, values):
    data=acceptance_values(values)
    if not any(data.values()):
        raise ValueError('Angiv mindst én acceptoplysning.')
    with closing(connect()) as conn:
        with conn:
            row=conn.execute('SELECT status FROM proposals WHERE id=?',(proposal_id,)).fetchone()
            if not row or row['status']!='Accepteret':
                raise ValueError('Tilbuddet skal være accepteret.')
            insert_acceptance(conn,proposal_id,data)
