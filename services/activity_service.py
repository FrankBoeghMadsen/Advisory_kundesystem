from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from repositories import q
from services.business_values import clean, parse_date

ACTIVE_ENGAGEMENTS = ('Planlagt', 'I gang', 'Afventer')


def dashboard_data(today=None):
    today = today or datetime.now(ZoneInfo('Europe/Copenhagen')).date()
    tracks = q('''SELECT t.*, c.name AS company FROM commercial_tracks t
                  JOIN companies c ON c.id=t.company_id''').to_dict('records')
    engagements = q('''SELECT e.*, t.company_id, c.name AS company FROM engagements e
        JOIN commercial_tracks t ON t.id=e.track_id JOIN companies c ON c.id=t.company_id''').to_dict('records')
    deliveries = q('''SELECT d.*, e.track_id, e.status AS engagement_status, e.title AS engagement_title,
        t.company_id, c.name AS company FROM deliverables d JOIN engagements e ON e.id=d.engagement_id
        JOIN commercial_tracks t ON t.id=e.track_id JOIN companies c ON c.id=t.company_id''').to_dict('records')
    proposals = q('''SELECT p.*, t.company_id, c.name AS company FROM proposals p
        JOIN commercial_tracks t ON t.id=p.track_id JOIN companies c ON c.id=t.company_id''').to_dict('records')
    meetings = q('''SELECT m.*, c.name AS company FROM meetings m
        LEFT JOIN companies c ON c.id=m.company_id''').to_dict('records')
    followups = q('''SELECT f.*, c.name AS company FROM followups f
        LEFT JOIN companies c ON c.id=f.company_id''').to_dict('records')
    return build_dashboard(today, tracks, engagements, deliveries, proposals, meetings, followups)


def build_dashboard(today, tracks, engagements, deliveries, proposals, meetings, followups):
    active = [e for e in engagements if e['status'] in ACTIVE_ENGAGEMENTS]
    open_deliveries = [d for d in deliveries if d['status'] not in ('Leveret','Annulleret')]
    delivery_rows = [d for d in open_deliveries if d['engagement_status'] in ACTIVE_ENGAGEMENTS]
    open_followups = [f for f in followups if (f.get('status') or 'Ny') not in ('Lukket','Arkiveret')]
    pending = [p for p in proposals if p['status'] in ('Sendt','Afventer')]
    open_tracks = [t for t in tracks if t['status'] in ('Åben','Afventer')]
    customers = {e['company_id']:dict(id=e['company_id'],company_id=e['company_id'],
        company=e['company'],title=e['company'],status='Aktiv kunde') for e in active}
    groups = {'Aktive kunder': list(customers.values()), 'Åbne forretningsforløb':open_tracks,
              'Tilbud afventer svar':pending, 'Aktive kundeopgaver':active,
              'Åbne leverancer':delivery_rows, 'Åbne opfølgninger':open_followups}
    events, undated = {}, []

    def add(kind, row, field, binding=True):
        day = parse_date(row.get(field))
        if not day:
            undated.append(dict(row, kind=kind, date_value=row.get(field) or ''))
            return
        if kind == 'Møde' and day < today:
            return
        key = (kind, int(row['id']))
        events[key] = dict(row, kind=kind, day=day, binding=binding,
                           overdue=day < today, related_followups=[])

    for row in delivery_rows:
        add('Leverancefrist',row,'due_date')
    for row in meetings:
        add('Møde',row,'meeting_date')
    for row in open_followups:
        delivery_id = clean(row.get('deliverable_id'))
        parent = events.get(('Leverancefrist',int(delivery_id))) if delivery_id is not None else None
        if parent and parse_date(row.get('due_date')) == parent['day'] and not (row.get('next_action') or '').strip():
            parent['related_followups'].append(row)
        else:
            add('Opfølgning',row,'due_date')
    for row in pending:
        add('Tilbudsfrist',row,'valid_until')
    for row in open_tracks:
        add('Forventet beslutning',row,'expected_decision_date',False)
    activities = sorted([e for e in events.values() if e['day'] <= today+timedelta(days=30)],
                        key=lambda e:(e['day'], {'Høj':0,'Middel':1,'Lav':2}.get(e.get('priority'),1), e.get('meeting_time') or '', e['kind'], int(e['id'])))
    return dict(groups=groups, activities=activities,
        overdue=sum(e['overdue'] for e in activities),
        next30=sum(not e['overdue'] for e in activities), undated=undated,
        rest_deliveries=[d for d in open_deliveries if d['engagement_status'] not in ACTIVE_ENGAGEMENTS],
        tracks=open_tracks, engagements=active, proposals=pending, followups=open_followups)
