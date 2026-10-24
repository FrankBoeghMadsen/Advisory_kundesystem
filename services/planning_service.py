from contextlib import closing
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from db import connect, utc_now_iso
from repositories import q
from services.activity_service import ACTIVE_ENGAGEMENTS
from services.business_values import parse_date

DAYS=['Mandag','Tirsdag','Onsdag','Torsdag','Fredag','Lørdag','Søndag']
MONTHS=['januar','februar','marts','april','maj','juni','juli','august','september','oktober','november','december']


def local_today():
    return datetime.now(ZoneInfo('Europe/Copenhagen')).date()


def danish_date(day):
    return f'{DAYS[day.weekday()]} {day.day}. {MONTHS[day.month-1]} {day.year}'


def valid_day(value):
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise ValueError('Vælg en gyldig dato.') from exc


def minutes(hours, allow_zero=False):
    try:
        value=Decimal(str(hours))*60
        if not value.is_finite() or value<0 or (not allow_zero and value==0) or value!=value.to_integral_value() or value>2147483647:
            raise ValueError
        return int(value)
    except (ValueError,InvalidOperation,TypeError) as exc:
        raise ValueError('Timer skal være et gyldigt positivt tal i hele minutter; kapacitet må også være nul.') from exc


def save_work_block(work_date, engagement_id, deliverable_id, description, hours, note='', record_id=None):
    day=valid_day(work_date)
    planned=minutes(hours)
    with closing(connect()) as conn:
        try:
            conn.execute('BEGIN IMMEDIATE')
            parent=conn.execute('SELECT title FROM engagements WHERE id=?',(engagement_id,)).fetchone()
            if not parent:
                raise ValueError('Vælg en eksisterende kundeopgave eller leverance.')
            if deliverable_id is not None:
                delivery=conn.execute('SELECT title FROM deliverables WHERE id=? AND engagement_id=?',(deliverable_id,engagement_id)).fetchone()
                if not delivery:
                    raise ValueError('Leverancen tilhører ikke kundeopgaven.')
            title=str(description or '').strip() or (delivery['title'] if deliverable_id is not None else parent['title'])
            values=(day,engagement_id,deliverable_id,title,planned,str(note or ''),utc_now_iso())
            if record_id is None:
                record_id=conn.execute('''INSERT INTO work_blocks
                    (work_date,engagement_id,deliverable_id,description,planned_minutes,note,updated_at,created_at)
                    VALUES(?,?,?,?,?,?,?,?)''',(*values,utc_now_iso())).lastrowid
            elif conn.execute('''UPDATE work_blocks SET work_date=?,engagement_id=?,deliverable_id=?,
                    description=?,planned_minutes=?,note=?,updated_at=? WHERE id=?''',(*values,record_id)).rowcount!=1:
                raise ValueError('Arbejdsblokken findes ikke længere.')
            conn.commit()
            return int(record_id)
        except Exception:
            conn.rollback()
            raise


def delete_work_block(record_id):
    with closing(connect()) as conn:
        with conn:
            if conn.execute('DELETE FROM work_blocks WHERE id=?',(record_id,)).rowcount!=1:
                raise ValueError('Arbejdsblokken findes ikke længere.')


def set_capacity(work_date, hours):
    day=valid_day(work_date)
    value=minutes(hours,True)
    with closing(connect()) as conn:
        with conn:
            conn.execute('''INSERT INTO daily_capacity VALUES(?,?) ON CONFLICT(work_date)
                DO UPDATE SET capacity_minutes=excluded.capacity_minutes''',(day,value))


def planning_targets():
    return q('''SELECT e.id AS engagement_id,NULL AS deliverable_id,e.title,c.name AS company
        FROM engagements e JOIN commercial_tracks t ON t.id=e.track_id JOIN companies c ON c.id=t.company_id
        UNION ALL SELECT e.id,d.id,d.title,c.name FROM deliverables d JOIN engagements e ON e.id=d.engagement_id
        JOIN commercial_tracks t ON t.id=e.track_id JOIN companies c ON c.id=t.company_id
        ORDER BY 4,3''').to_dict('records')


def week_data(day):
    start=day-timedelta(days=day.weekday())
    end=start+timedelta(days=6)
    blocks=q('''SELECT b.*,e.track_id,e.title AS engagement_title,e.status AS engagement_status,
        d.due_date,d.status AS delivery_status,c.name AS company FROM work_blocks b
        JOIN engagements e ON e.id=b.engagement_id JOIN commercial_tracks t ON t.id=e.track_id
        JOIN companies c ON c.id=t.company_id LEFT JOIN deliverables d ON d.id=b.deliverable_id
        WHERE b.work_date BETWEEN ? AND ? ORDER BY b.work_date,b.id''',(start.isoformat(),end.isoformat())).to_dict('records')
    capacities={r['work_date']:r['capacity_minutes'] for r in q('SELECT * FROM daily_capacity WHERE work_date BETWEEN ? AND ?',
        (start.isoformat(),end.isoformat())).to_dict('records')}
    deadlines=q('''SELECT d.*,e.track_id,e.status AS engagement_status,c.name AS company FROM deliverables d
        JOIN engagements e ON e.id=d.engagement_id JOIN commercial_tracks t ON t.id=e.track_id
        JOIN companies c ON c.id=t.company_id WHERE d.due_date BETWEEN ? AND ?
        AND d.status NOT IN ('Leveret','Annulleret')''',(start.isoformat(),end.isoformat())).to_dict('records')
    deadlines=[d for d in deadlines if d['engagement_status'] in ACTIVE_ENGAGEMENTS]
    return build_week(start,blocks,capacities,deadlines)


def build_week(start, blocks, capacities, deadlines):
    # Calendar occupancy can later be supplied as a separate, deduplicated source.
    # Only explicitly stored work blocks consume capacity in this implementation.
    days=[]
    for offset in range(7):
        day=start+timedelta(days=offset)
        iso=day.isoformat()
        daily=[b for b in blocks if b['work_date']==iso]
        capacity=capacities.get(iso,420 if day.weekday()<5 else 0)
        planned=sum(b['planned_minutes'] for b in daily)
        late=[b for b in daily if b.get('delivery_status') not in ('Leveret','Annulleret')
              and parse_date(b.get('due_date')) and day>parse_date(b['due_date'])]
        days.append(dict(day=day,blocks=daily,capacity=capacity,planned=planned,remaining=capacity-planned,
                         after_deadline=late,deadlines=[d for d in deadlines if d['due_date']==iso]))
    return dict(start=start,days=days,planned=sum(d['planned'] for d in days),
                capacity=sum(d['capacity'] for d in days),remaining=sum(d['remaining'] for d in days))
