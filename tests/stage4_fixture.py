from contextlib import closing

import db
from services.business_service import save_business_record, create_engagement_from_proposal


def populate():
    db.init_db()
    with closing(db.connect()) as conn:
        actor = conn.execute("INSERT INTO companies(name,created_at) VALUES('TEST Apotek',?)", (db.utc_now_iso(),)).lastrowid
        conn.commit()
    track = save_business_record('commercial_tracks', dict(company_id=actor, title='Syntetisk rådgivningsforløb',
        need_description='Illustrativ regulatorisk rådgivning', status='Afventer'))
    pid = save_business_record('proposals', dict(track_id=track,title='Accepteret testtilbud',version=1,
        status='Accepteret',fee_model='Fast pris',offered_fee_ex_vat=25000))
    eid = create_engagement_from_proposal(pid,'Aktiv testopgave','Syntetisk opgavebeskrivelse',
        'I gang','','','Fast pris',25000,'Afgrænset testomfang')
    save_business_record('proposals',dict(track_id=track,title='Testtilbud uden honorar',version=2,
        status='Kladde',fee_model='Endnu ikke aftalt',offered_fee_ex_vat=None))
    save_business_record('deliverables',dict(engagement_id=eid,title='Testleverance',status='I gang',due_date='2026-11-20'))
    with closing(db.connect()) as conn:
        conn.execute('''INSERT INTO followups(company_id,commercial_track_id,title,next_action,due_date,status,created_at)
            VALUES(?,?,?,?,?,?,?)''', (actor,track,'Afklar opgavens omfang','Følg op på kundens accept','2026-11-01','Afventer',db.utc_now_iso()))
        conn.commit()
    return track, pid, eid
