"""Project core only: no commercial creation, finance, or activity automation."""
from contextlib import closing
import sqlite3

from db import connect, utc_now_iso

PROJECT_STATUSES = ['Planlagt','Aktivt','Afventer','Afsluttet','Annulleret']
WORKSTREAM_STATUSES = ['Planlagt','I gang','Afventer','Afsluttet','Annulleret']
ROLES = {'Koordinator':'coordinator','Aftalepart':'contracting_party','Betaler':'payer',
         'Deltager':'participant','Begunstiget':'beneficiary'}


def _exists(conn, table, record_id):
    if not conn.execute(f'SELECT 1 FROM {table} WHERE id=?',(record_id,)).fetchone():
        raise ValueError('Den valgte post findes ikke.')


def save_project(title, purpose='', status='Planlagt', project_id=None):
    if not title.strip() or status not in PROJECT_STATUSES:
        raise ValueError('Angiv en titel og en gyldig projektstatus.')
    with closing(connect()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        now=utc_now_iso()
        if project_id is None:
            return conn.execute('INSERT INTO projects(title,purpose,status,created_at,updated_at) VALUES(?,?,?,?,?)',
                                (title.strip(),purpose,status,now,now)).lastrowid
        _exists(conn,'projects',project_id)
        conn.execute('UPDATE projects SET title=?,purpose=?,status=?,updated_at=? WHERE id=?',
                     (title.strip(),purpose,status,now,project_id))
        return project_id


def save_participant(project_id, company_id, roles):
    if set(roles)-set(ROLES):
        raise ValueError('Ukendt projektrolle.')
    with closing(connect()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        _exists(conn,'projects',project_id)
        _exists(conn,'companies',company_id)
        values=[int(label in roles) for label in ROLES]
        conn.execute('''INSERT INTO project_companies(project_id,company_id,coordinator,contracting_party,payer,participant,beneficiary)
            VALUES(?,?,?,?,?,?,?) ON CONFLICT(project_id,company_id) DO UPDATE SET
            coordinator=excluded.coordinator,contracting_party=excluded.contracting_party,payer=excluded.payer,
            participant=excluded.participant,beneficiary=excluded.beneficiary''',(project_id,company_id,*values))


def save_workstream(project_id, title, company_id=None, status='Planlagt', workstream_id=None):
    if not title.strip() or status not in WORKSTREAM_STATUSES:
        raise ValueError('Angiv en titel og en gyldig sporstatus.')
    with closing(connect()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        _exists(conn,'projects',project_id)
        if company_id is not None and not conn.execute('SELECT 1 FROM project_companies WHERE project_id=? AND company_id=?',(project_id,company_id)).fetchone():
            raise ValueError('Virksomheden skal være projektdeltager.')
        now=utc_now_iso()
        if workstream_id is None:
            return conn.execute('INSERT INTO project_workstreams(project_id,title,company_id,status,created_at,updated_at) VALUES(?,?,?,?,?,?)',
                (project_id,title.strip(),company_id,status,now,now)).lastrowid
        if not conn.execute('SELECT 1 FROM project_workstreams WHERE id=? AND project_id=?',(workstream_id,project_id)).fetchone():
            raise ValueError('Arbejdssporet hører ikke til projektet.')
        conn.execute('UPDATE project_workstreams SET title=?,company_id=?,status=?,updated_at=? WHERE id=?',
            (title.strip(),company_id,status,now,workstream_id))
        return workstream_id


def link_track(project_id, track_id):
    with closing(connect()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        _exists(conn,'projects',project_id)
        row=conn.execute('SELECT company_id FROM commercial_tracks WHERE id=?',(track_id,)).fetchone()
        if row is None or not conn.execute('SELECT 1 FROM project_companies WHERE project_id=? AND company_id=?',(project_id,row[0])).fetchone():
            raise ValueError('Forløbets virksomhed skal være projektdeltager.')
        previous=conn.execute('SELECT project_id FROM project_tracks WHERE track_id=?',(track_id,)).fetchone()
        if previous and previous[0]!=project_id:
            raise ValueError('Forløbet er knyttet til et andet projekt. Frakobl det først.')
        if not previous:
            conn.execute('INSERT INTO project_tracks(project_id,track_id) VALUES(?,?)',(project_id,track_id))


def remove_relation(kind, project_id, record_id):
    statements={'participant':('project_companies','company_id'),
                'track':('project_tracks','track_id'), 'workstream':('project_workstreams','id')}
    if kind not in statements:
        raise ValueError('Ukendt relation.')
    table,column=statements[kind]
    with closing(connect()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        try:
            conn.execute(f'DELETE FROM {table} WHERE project_id=? AND {column}=?',(project_id,record_id))
        except sqlite3.IntegrityError as exc:
            raise ValueError('Deltageren har tilknyttede spor eller forløb. Frakobl dem først.') from exc
