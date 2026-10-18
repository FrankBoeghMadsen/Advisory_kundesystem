"""Synthetic project actors only; do not seed the old company catalogue."""
from contextlib import closing

import db


def populate():
    if db.APP_MODE not in ('test','development'):
        raise RuntimeError('Syntetiske data kræver isoleret test eller udvikling.')
    with closing(db.connect()) as conn:
        db.migrate_db(conn)
        now=db.utc_now_iso()
        a=conn.execute("INSERT INTO companies(name,created_at) VALUES('TEST Alfa',?)",(now,)).lastrowid
        b=conn.execute("INSERT INTO companies(name,created_at) VALUES('TEST Beta',?)",(now,)).lastrowid
        track=conn.execute("INSERT INTO commercial_tracks(company_id,title,created_at,updated_at) VALUES(?,'TEST Eksisterende behov',?,?)",(a,now,now)).lastrowid
        conn.commit()
    return a,b,track
