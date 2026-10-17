from contextlib import closing

import db
from tests.stage4_fixture import populate as populate_stage4
from services.business_service import record_amendment


def populate():
    if db.APP_MODE not in ('test','development'):
        raise RuntimeError('Testdata kræver en isoleret udviklings- eller testdatabase.')
    track,pid,eid=populate_stage4()
    with closing(db.connect()) as conn:
        actor=conn.execute('SELECT company_id FROM commercial_tracks WHERE id=?',(track,)).fetchone()[0]
        conn.execute("UPDATE companies SET name='TEST Glostrup Apotek' WHERE id=?",(actor,))
        conn.execute("UPDATE deliverables SET title='Juridisk vurderingsnotat om medicinsk cannabis',due_date='2026-10-24',priority='Høj' WHERE engagement_id=?",(eid,))
        conn.execute("INSERT INTO meetings(company_id,title,meeting_date,raw_text,created_at) VALUES(?,'Test af kundemøde','2026-10-22','Syntetisk referat',?)",(actor,db.utc_now_iso()))
        conn.commit()
    record_amendment(eid,'2026-10-18','Forslag til yderligere rådgivning','',30000)
    return track,pid,eid
