"""Direct editing of existing activities, without copying linked records."""
import streamlit as st

from db import connect, utc_now_iso
from services.business_values import parse_date, iso_date


def require_title(title):
    if not title or not title.strip():
        raise ValueError('Angiv en beskrivende titel.')
    return title.strip()


def delete_activity(table, record_id, confirmed=False):
    if table not in ('meetings', 'followups'):
        raise ValueError('Ukendt aktivitet.')
    if not confirmed:
        raise ValueError('Bekræft sletningen først.')
    conn = connect()
    try:
        conn.execute('BEGIN IMMEDIATE')
        with conn:
            if table == 'meetings':
                if conn.execute("SELECT 1 FROM followups WHERE source_type='AI-opfølgning' AND source_id=? LIMIT 1", (record_id,)).fetchone():
                    raise ValueError('Mødet har en tilknyttet opfølgning og kan ikke slettes her. Indholdet er bevaret.')
                for dependent, column in (('uploaded_documents','meeting_id'),
                                          ('briefings','meeting_id'),
                                          ('observations','related_meeting_id')):
                    if conn.execute(f'SELECT 1 FROM {dependent} WHERE {column}=? LIMIT 1', (record_id,)).fetchone():
                        raise ValueError('Mødet har tilknyttede dokumenter, briefinger eller observationer og kan ikke slettes her. Indholdet er bevaret.')
                conn.execute('DELETE FROM meeting_tracks WHERE meeting_id=?', (record_id,))
            conn.execute(f'DELETE FROM {table} WHERE id=?', (record_id,))
    finally:
        conn.close()


def meeting_editor(record_id):
    conn = connect()
    row = conn.execute('SELECT * FROM meetings WHERE id=?', (record_id,)).fetchone()
    conn.close()
    if row is None:
        return
    prefix = f'meeting_edit_{record_id}'
    with st.form(prefix, enter_to_submit=False):
        title = st.text_input('Titel', row['title'] or '', key=prefix+'_title')
        meeting_date = st.date_input('Dato', value=parse_date(row['meeting_date']), format='DD-MM-YYYY', key=prefix+'_date')
        time = st.text_input('Tid', row['meeting_time'] or '')
        location = st.text_input('Sted', row['location'] or '')
        participants = st.text_input('Deltagere', row['participants'] or '')
        summary = st.text_area('Resume', row['summary'] or '')
        takeaways = st.text_area('Hvad lærte vi', row['key_takeaways'] or '')
        steps = st.text_area('Næste skridt', row['next_steps'] or '')
        if row['meeting_date'] and not parse_date(row['meeting_date']):
            st.caption('Eksisterende datotekst: '+row['meeting_date'])
        if st.form_submit_button('Gem mødeændringer'):
            try:
                title = require_title(title)
                conn = connect()
                with conn:
                    conn.execute('UPDATE meetings SET title=?,meeting_date=?,meeting_time=?,location=?,participants=?,summary=?,key_takeaways=?,next_steps=?,updated_at=? WHERE id=?',
                                 (title,iso_date(meeting_date) if meeting_date else (row['meeting_date'] if not parse_date(row['meeting_date']) else ''),time,location,participants,summary,takeaways,steps,utc_now_iso(),record_id))
                conn.close()
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    deletion_controls('meetings', record_id)


def deletion_controls(table, record_id):
    confirmed = st.checkbox('Bekræft permanent sletning af denne registrering', key=f'delete_confirm_{table}_{record_id}')
    if st.button('Slet registrering', key=f'delete_{table}_{record_id}', disabled=not confirmed):
        try:
            delete_activity(table, record_id, confirmed)
            st.session_state.pop('record_focus', None)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
