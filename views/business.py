import json
from datetime import date
from zoneinfo import ZoneInfo
from datetime import datetime

import streamlit as st

from app_config import (TRACK_STATUSES, TRACK_CLOSE_REASONS, PROPOSAL_STATUSES,
                        ENGAGEMENT_STATUSES, DELIVERABLE_STATUSES, FEE_MODELS)
from repositories import q
from services.business_service import (save_business_record, next_proposal_version,
    create_engagement_from_proposal, record_amendment, set_track_meetings,
    set_track_followups, set_deliverable_followups)
from services.business_values import (clean, number_text, parse_danish_number,
                                      fee_text, parse_date, date_text, iso_date)

FIELD_LABELS = {'title':'Titel', 'scope':'Omfang', 'deliverables_summary':'Leverancer',
    'assumptions':'Forudsætninger', 'fee_model':'Honorarmodel', 'offered_fee_ex_vat':'Tilbudt honorar',
    'fee_note':'Honorarnote', 'status':'Status', 'sent_date':'Afsendelsesdato',
    'valid_until':'Gyldigt til', 'document_reference':'Dokumentreference',
    'max_hours':'Timeloft', 'fee_cap_ex_vat':'Honorarloft', 'included_hours':'Inkluderede timer',
    'version':'Version', 'track_id':'Forretningsforløb'}


def _select(label, options, value, key):
    return st.selectbox(label, options, index=options.index(value) if value in options else 0, key=key)


def _date(label, value, key):
    parsed = parse_date(value)
    if value and parsed is None:
        st.warning(f'{label}: den eksisterende tekst »{value}« bevares, indtil du vælger en kalenderdato.')
    selected = st.date_input(label, value=parsed, min_value=date(1900, 1, 1),
                         max_value=date(2100, 12, 31), format='DD-MM-YYYY', key=key)
    return value if value and parsed is None and selected is None else selected


def _number(label, value, key):
    return st.text_input(label, value=number_text(value), key=key)


def _fees(prefix, row, agreed=False):
    model = _select('Honorarmodel', FEE_MODELS, row.get('fee_model', FEE_MODELS[-1]), prefix+'_model')
    label = 'Timepris ekskl. moms' if model == 'Timepris' else 'Samlet honorar ekskl. moms'
    column = 'agreed_fee_ex_vat' if agreed else 'offered_fee_ex_vat'
    # All fields are optional; an empty string differs from an explicit zero.
    amount = _number(label, row.get(column), prefix+'_amount') if model != 'Endnu ikke aftalt' or clean(row.get(column)) is not None else ''
    values = {column: amount,
              'max_hours': '', 'fee_cap_ex_vat': '', 'included_hours': ''}
    if model == 'Timepris':
        values['max_hours'] = _number('Aftalt maksimalt antal timer', row.get('max_hours'), prefix+'_hours')
        values['fee_cap_ex_vat'] = _number('Aftalt honorarloft ekskl. moms', row.get('fee_cap_ex_vat'), prefix+'_cap')
    elif model == 'Klippekort / retainer':
        values['included_hours'] = _number('Inkluderede timer', row.get('included_hours'), prefix+'_included')
    values['fee_model'] = model
    values['fee_note'] = st.text_area('Honorarnote', row.get('fee_note') or '', key=prefix+'_fee_note', height=80)
    return values


def _parsed_fees(values):
    return {key: parse_danish_number(value) if key not in ('fee_model', 'fee_note') else value
            for key, value in values.items()}


def _save(table, values, record_id=None, reason=''):
    try:
        save_business_record(table, values, record_id, reason)
    except (ValueError, RuntimeError) as exc:
        st.error(str(exc))
        return
    st.rerun()


def _followups(track_id, prefix):
    rows = q('''SELECT id, title, next_action, due_date, status, person FROM followups
        WHERE commercial_track_id=? AND COALESCE(status,'Ny') NOT IN ('Lukket','Arkiveret')
        ORDER BY CASE WHEN due_date='' THEN 1 ELSE 0 END, due_date, created_at''', (track_id,))
    if not len(rows):
        st.caption('Ingen åben opfølgning tilknyttet.')
    for _, item in rows.iterrows():
        owner = 'Afventer' if item['status'] == 'Afventer' else 'Næste handling'
        st.write(f"**{owner}:** {item['next_action'] or item['title']}")
        st.caption(f"{date_text(item['due_date'])} · {item['person'] or 'Ingen person angivet'} · {item['status']}")
    if st.button('Åbn opfølgninger', key=prefix+'_followups'):
        st.session_state['page'] = 'Opgaver'
        st.rerun()


def _track_editor(row, companies):
    prefix = f"track_{row.get('id', 'new')}"
    ids = [None] + [int(x) for x in companies['id']]
    company_id = st.selectbox('Aktør', ids, index=ids.index(row.get('company_id')) if row.get('company_id') in ids else 0,
        format_func=lambda x: 'Vælg aktør' if x is None else companies.loc[companies['id']==x, 'name'].iloc[0],
        key=prefix+'_company', disabled=bool(row.get('id')))
    title = st.text_input('Titel', row.get('title', ''), key=prefix+'_title')
    need = st.text_area('Konkret behov / mulighed', row.get('need_description') or '', key=prefix+'_need')
    area = st.text_input('Rådgivningsområde', row.get('service_area') or '', key=prefix+'_area')
    status = _select('Status', TRACK_STATUSES, row.get('status', 'Åben'), prefix+'_status')
    decision = _date('Forventet beslutningsdato', row.get('expected_decision_date'), prefix+'_decision')
    reason = _select('Afslutningsårsag', TRACK_CLOSE_REASONS, row.get('close_reason', ''), prefix+'_reason') if status == 'Lukket' else ''
    contacts = q('SELECT id, name FROM contacts WHERE company_id=? ORDER BY name', (company_id,)) if company_id else []
    contact_id = None
    if len(contacts):
        contact_ids = [None] + [int(x) for x in contacts['id']]
        current = clean(row.get('primary_contact_id'))
        contact_id = st.selectbox('Primær kontakt', contact_ids,
            index=contact_ids.index(current) if current in contact_ids else 0,
            format_func=lambda x: 'Ingen valgt' if x is None else contacts.loc[contacts['id']==x, 'name'].iloc[0], key=prefix+'_contact')
    if st.button('Gem forløb', key=prefix+'_save', type='primary'):
        if company_id is None:
            st.error('Vælg en aktør.')
        else:
            _save('commercial_tracks', dict(company_id=company_id, title=title,
                need_description=need, service_area=area, status=status,
                expected_decision_date=iso_date(decision), close_reason=reason,
                closed_at=(row.get('closed_at') or datetime.now(ZoneInfo('Europe/Copenhagen')).isoformat()) if status=='Lukket' else '',
                primary_contact_id=contact_id), row.get('id'))


def _links(row):
    track_id, company_id = int(row['id']), int(row['company_id'])
    meetings = q('SELECT id, title, meeting_date FROM meetings WHERE company_id=? ORDER BY meeting_date DESC', (company_id,))
    linked = q('SELECT meeting_id FROM meeting_tracks WHERE track_id=?', (track_id,))
    ids = [int(x) for x in meetings['id']]
    selected = st.multiselect('Møder', ids, default=[int(x) for x in linked['meeting_id'] if x in ids],
        format_func=lambda x: f"{date_text(meetings.loc[meetings['id']==x,'meeting_date'].iloc[0])} · {meetings.loc[meetings['id']==x,'title'].iloc[0]}", key=f'meeting_links_{track_id}')
    if st.button('Gem mødekoblinger', key=f'save_meetings_{track_id}'):
        set_track_meetings(track_id, selected)
        st.rerun()
    followups = q('SELECT id, title FROM followups WHERE company_id=? ORDER BY created_at DESC', (company_id,))
    linked_f = q('SELECT id FROM followups WHERE commercial_track_id=?', (track_id,))
    ids_f = [int(x) for x in followups['id']]
    selected_f = st.multiselect('Opfølgninger', ids_f, default=[int(x) for x in linked_f['id'] if x in ids_f],
        format_func=lambda x: followups.loc[followups['id']==x, 'title'].iloc[0], key=f'follow_links_{track_id}')
    if st.button('Gem opfølgningskoblinger', key=f'save_follow_{track_id}'):
        set_track_followups(track_id, selected_f)
        st.rerun()


def _proposal_editor(row, track_id, correction=False):
    prefix = f"proposal_{track_id}_{row.get('id', 'new')}"
    title = st.text_input('Tilbudstitel', row.get('title', ''), key=prefix+'_title')
    scope = st.text_area('Omfang', row.get('scope') or '', key=prefix+'_scope')
    deliverables = st.text_area('Forventede leverancer', row.get('deliverables_summary') or '', key=prefix+'_deliverables')
    assumptions = st.text_area('Forudsætninger', row.get('assumptions') or '', key=prefix+'_assumptions')
    fees = _fees(prefix, row)
    status = 'Accepteret' if correction else _select('Status', PROPOSAL_STATUSES, row.get('status', 'Kladde'), prefix+'_status')
    sent_default = row.get('sent_date')
    if status == 'Sendt' and not sent_default:
        sent_default = datetime.now(ZoneInfo('Europe/Copenhagen')).date()
    sent = _date('Afsendelsesdato', sent_default, prefix+'_sent_'+('sent' if status=='Sendt' else 'other'))
    valid = _date('Gyldigt til', row.get('valid_until'), prefix+'_valid')
    reference = st.text_input('Reference til tilbudsdokument', row.get('document_reference') or '', key=prefix+'_doc')
    reason = st.text_area('Begrundelse for korrektion', key=prefix+'_reason') if correction else ''
    if st.button('Gem korrektion' if correction else 'Gem tilbud', key=prefix+'_save', type='primary'):
        try:
            values = dict(track_id=track_id, title=title, version=int(row.get('version') or next_proposal_version(track_id)),
                scope=scope, deliverables_summary=deliverables, assumptions=assumptions,
                status=status, sent_date=iso_date(sent), valid_until=iso_date(valid), document_reference=reference,
                **_parsed_fees(fees))
            _save('proposals', values, row.get('id'), reason)
        except ValueError as exc:
            st.error(str(exc))


def _engagement_editor(row, track_id, proposal=None):
    prefix = f"engagement_{track_id}_{row.get('id', 'new')}_{proposal['id'] if proposal else 'direct'}"
    title = st.text_input('Opgavetitel', row.get('title') or '', key=prefix+'_title')
    description = st.text_area('Aktuel opgavebeskrivelse', row.get('description') or '', key=prefix+'_desc')
    status = _select('Opgavestatus', ENGAGEMENT_STATUSES, row.get('status', 'Planlagt'), prefix+'_status')
    start = _date('Startdato', row.get('start_date'), prefix+'_start')
    end = _date('Forventet slutdato', row.get('target_end_date'), prefix+'_end')
    completed = _date('Faktisk afslutningsdato', row.get('completed_at'), prefix+'_completed')
    fees = _fees(prefix, row, agreed=True)
    actual, reuse, reuse_note = None, 'Ikke vurderet', ''
    outcome, future = row.get('outcome_notes') or '', row.get('future_collaboration_note') or ''
    with st.container():
        st.markdown('**Evaluering og læring**')
        actual = _number('Faktisk anvendte timer', row.get('actual_hours'), prefix+'_actual')
        reuse = _select('Genanvendelsespotentiale', ['Ikke vurderet','Ja','Nej'], row.get('reuse_potential', 'Ikke vurderet'), prefix+'_reuse')
        reuse_note = st.text_area('Genanvendelig viden, metoder eller værktøjer', row.get('reuse_notes') or '', key=prefix+'_reuse_note')
        outcome = st.text_area('Resultat / læring', outcome, key=prefix+'_outcome')
        future = st.text_area('Muligt fremtidigt samarbejde', future, key=prefix+'_future')
    if st.button('Accepter tilbud og opret kundeopgave' if proposal else 'Gem kundeopgave', key=prefix+'_save', type='primary'):
        try:
            parsed = _parsed_fees(fees)
            parsed_actual = parse_danish_number(actual)
            if not title.strip():
                raise ValueError('Opgavetitel skal udfyldes.')
            if proposal:
                created_id = create_engagement_from_proposal(int(proposal['id']), title, description, status,
                    iso_date(start), iso_date(end), parsed['fee_model'], parsed['agreed_fee_ex_vat'],
                    parsed['fee_note'], parsed.get('max_hours'), parsed.get('fee_cap_ex_vat'), parsed.get('included_hours'))
                save_business_record('engagements', dict(title=title, completed_at=iso_date(completed),
                    actual_hours=parsed_actual, reuse_potential=reuse,
                    reuse_notes=reuse_note, outcome_notes=outcome, future_collaboration_note=future), created_id)
                st.rerun()
            else:
                _save('engagements', dict(track_id=track_id, title=title, description=description,
                    status=status, start_date=iso_date(start), target_end_date=iso_date(end), completed_at=iso_date(completed),
                    outcome_notes=outcome, future_collaboration_note=future, actual_hours=parsed_actual,
                    reuse_potential=reuse, reuse_notes=reuse_note, **parsed), row.get('id'))
        except ValueError as exc:
            st.error(str(exc))


def _fee_details(row, agreed=False):
    st.write(f"**{row['fee_model']}:** {fee_text(row['agreed_fee_ex_vat' if agreed else 'offered_fee_ex_vat'], row['fee_model'])}")
    for key, label in [('max_hours','Aftalt timeloft'),('fee_cap_ex_vat','Honorarloft ekskl. moms'),('included_hours','Inkluderede timer')]:
        if clean(row.get(key)) is not None:
            st.caption(f'{label}: {number_text(row[key])}')
    if row.get('fee_note'):
        st.write(row['fee_note'])


def _proposals(track_id):
    with st.expander('Opret tilbud'):
        _proposal_editor({}, track_id)
    rows = q('SELECT * FROM proposals WHERE track_id=? ORDER BY version DESC', (track_id,))
    for _, series in rows.iterrows():
        row = series.to_dict()
        proposal_id = int(row['id'])
        with st.container(border=True):
            st.markdown(f"**{row['title']} · v{row['version']}**")
            st.caption(f"{row['status']} · Afsendt: {date_text(row['sent_date'])} · Gyldigt til: {date_text(row['valid_until'])}")
            _fee_details(row)
            if row['scope']:
                st.write(row['scope'])
            with st.expander('Leverancer, forudsætninger og dokument'):
                st.write(row['deliverables_summary'] or 'Ingen leverancer beskrevet.')
                st.write(row['assumptions'] or 'Ingen særlige forudsætninger.')
                st.write(row['document_reference'] or 'Ingen dokumentreference.')
            if row['status'] == 'Accepteret':
                st.caption('Accepteret aftalegrundlag · skrivebeskyttet')
                with st.expander('Korrigér registreringsfejl'):
                    if st.checkbox('Jeg vil korrigere en registreringsfejl', key=f'correct_{proposal_id}'):
                        _proposal_editor(row, track_id, correction=True)
                with st.expander('Ændringslog'):
                    logs = q('SELECT * FROM proposal_changes WHERE proposal_id=? ORDER BY changed_at DESC', (proposal_id,))
                    if not len(logs):
                        st.caption('Ingen korrektioner.')
                    for _, log in logs.iterrows():
                        st.write(f"{log['changed_at']} · {log['reason']}")
                        old, new = json.loads(log['previous_values']), json.loads(log['new_values'])
                        st.table([{'Felt': FIELD_LABELS.get(key,key),
                                   'Tidligere': str(old[key]) if old[key] is not None else 'Ikke registreret',
                                   'Ny': str(value) if value is not None else 'Ikke registreret'} for key, value in new.items()])
            else:
                with st.expander('Redigér tilbud'):
                    if row['status'] in ('Sendt','Afventer'):
                        st.warning('Du ændrer et allerede fremsendt tilbud.')
                    _proposal_editor(row, track_id)
            linked = q('SELECT id FROM engagements WHERE accepted_proposal_id=?', (proposal_id,))
            if not len(linked):
                with st.expander('Opret kundeopgave fra tilbud'):
                    suggested_description = '\n\n'.join(filter(None, [row['scope'], row['deliverables_summary'], row['assumptions']]))
                    suggestion = dict(row, id=None, description=suggested_description, status='Planlagt',
                                      agreed_fee_ex_vat=row['offered_fee_ex_vat'])
                    _engagement_editor(suggestion, track_id, row)
            else:
                st.caption('Kundeopgave oprettet fra tilbuddet.')


def _deliverable_editor(row, engagement_id):
    prefix = f"deliverable_{engagement_id}_{row.get('id', 'new')}"
    title = st.text_input('Leverancetitel', row.get('title') or '', key=prefix+'_title')
    description = st.text_area('Beskrivelse', row.get('description') or '', key=prefix+'_desc')
    due = _date('Leverancedeadline', row.get('due_date'), prefix+'_due')
    status = _select('Status', DELIVERABLE_STATUSES, row.get('status','Ikke startet'), prefix+'_status')
    priority = _select('Prioritet', ['Lav','Middel','Høj'], row.get('priority','Middel'), prefix+'_priority')
    responsible = st.text_input('Ansvarlig / note', row.get('responsible_note') or '', key=prefix+'_responsible')
    if st.button('Gem leverance', key=prefix+'_save'):
        _save('deliverables', dict(engagement_id=engagement_id, title=title, description=description,
            due_date=iso_date(due), status=status, priority=priority, responsible_note=responsible,
            completed_at=row.get('completed_at') or ''), row.get('id'))


def _engagements(track_id):
    with st.expander('Opret kundeopgave uden tilbud'):
        _engagement_editor({}, track_id)
    for _, series in q('SELECT * FROM engagements WHERE track_id=? ORDER BY created_at DESC', (track_id,)).iterrows():
        row = series.to_dict()
        eid = int(row['id'])
        with st.container(border=True):
            st.markdown(f"**{row['title']}**")
            st.caption(f"{row['status']} · Start: {date_text(row['start_date'])} · Slut: {date_text(row['target_end_date'])}")
            _fee_details(row, True)
            if row['description']:
                st.write(row['description'])
            with st.expander('Redigér kundeopgave'):
                _engagement_editor(row, track_id)
            with st.expander('Oprindelig aftale'):
                original = json.loads(row['original_agreement'] or '{}')
                st.write(original.get('title') or row['title'])
                st.write(original.get('description') or '')
                st.write(fee_text(original.get('agreed_fee_ex_vat'), original.get('fee_model','Fast pris')))
                st.write(original.get('fee_note') or '')
                for field, label in [('max_hours','Aftalt timeloft'), ('fee_cap_ex_vat','Honorarloft'),
                                     ('included_hours','Inkluderede timer')]:
                    if original.get(field) is not None:
                        st.caption(f'{label}: {number_text(original[field])}')
                st.caption(f"Start: {date_text(original.get('start_date'))} · Slut: {date_text(original.get('target_end_date'))}")
                if clean(row['accepted_proposal_id']) is not None:
                    st.caption(f"Grundlag: tilbud #{int(row['accepted_proposal_id'])}")
            with st.expander('Aftaleændringer'):
                for _, amendment in q('SELECT * FROM engagement_amendments WHERE engagement_id=? ORDER BY id DESC', (eid,)).iterrows():
                    st.write(f"**{date_text(amendment['amendment_date'])}** · {amendment['description']}")
                    if clean(amendment['new_fee']) is not None:
                        st.caption(f"Honorar: {number_text(amendment['previous_fee']) or 'Ikke registreret'} → {number_text(amendment['new_fee'])}")
                    st.write(amendment['acceptance_reference'] or '')
                day = _date('Ændringsdato', None, f'amendment_day_{eid}')
                description = st.text_area('Beskrivelse af aftaleændring', key=f'amendment_desc_{eid}')
                new_fee = _number('Nyt aftalt honorar ekskl. moms', None, f'amendment_fee_{eid}')
                reference = st.text_input('Reference til kundens accept / dokumentation', key=f'amendment_ref_{eid}')
                if st.button('Registrér aftaleændring', key=f'amendment_save_{eid}'):
                    try:
                        record_amendment(eid, iso_date(day), description, reference, parse_danish_number(new_fee))
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            with st.expander('Evaluering'):
                st.write(f"Faktisk anvendte timer: {number_text(row['actual_hours']) or 'Ikke registreret'}")
                st.write(f"Genanvendelsespotentiale: {row['reuse_potential']}")
                st.write(row['reuse_notes'] or '')
                st.write(row['outcome_notes'] or '')
                st.write(row['future_collaboration_note'] or '')
            st.markdown('**Leverancer**')
            for _, delivery_series in q('SELECT * FROM deliverables WHERE engagement_id=? ORDER BY due_date, id', (eid,)).iterrows():
                delivery = delivery_series.to_dict()
                st.write(f"{delivery['title']} · {delivery['status']} · {date_text(delivery['due_date'])}")
                with st.expander(f"Redigér leverance: {delivery['title']}"):
                    _deliverable_editor(delivery, eid)
                    candidates = q('SELECT id, title FROM followups WHERE company_id=(SELECT company_id FROM commercial_tracks WHERE id=?)', (track_id,))
                    linked = q('SELECT id FROM followups WHERE deliverable_id=?', (int(delivery['id']),))
                    ids = [int(x) for x in candidates['id']]
                    chosen = st.multiselect('Opfølgninger til leverancen', ids, default=[int(x) for x in linked['id'] if x in ids],
                        format_func=lambda x: candidates.loc[candidates['id']==x,'title'].iloc[0], key=f"delivery_links_{delivery['id']}")
                    if st.button('Gem leverancekoblinger', key=f"delivery_link_save_{delivery['id']}"):
                        set_deliverable_followups(int(delivery['id']), chosen)
                        st.rerun()
            with st.expander('Opret leverance'):
                _deliverable_editor({}, eid)


def render():
    st.subheader('Forretning')
    companies = q('SELECT id, name FROM companies ORDER BY name')
    tracks = q('''SELECT t.*, c.name AS company FROM commercial_tracks t
        JOIN companies c ON c.id=t.company_id ORDER BY t.created_at DESC, t.id DESC''')
    preferred_track = st.session_state.pop('business_track_id', None)
    if preferred_track is not None and preferred_track in tracks['id'].tolist():
        st.session_state['business_actor_filter'] = 'Alle'
        st.session_state['business_status_filter'] = TRACK_STATUSES
        st.session_state['business_search'] = ''
        st.session_state['business_selected_track'] = preferred_track
    with st.expander('Opret forretningsforløb'):
        _track_editor({}, companies)
    if not len(tracks):
        st.info('Ingen forretningsforløb registreret.')
        return
    actor_options = ['Alle'] + sorted(tracks['company'].unique().tolist())
    preferred = st.session_state.pop('business_company_id', None)
    if preferred is not None:
        match = companies[companies['id']==preferred]
        if len(match) and match.iloc[0]['name'] in actor_options:
            st.session_state['business_actor_filter'] = match.iloc[0]['name']
    actor = _select('Kunde / aktør', actor_options, 'Alle', 'business_actor_filter')
    statuses = st.multiselect('Status på forløb', TRACK_STATUSES, default=TRACK_STATUSES, key='business_status_filter')
    search = st.text_input('Søg efter forløb', key='business_search')
    shown = tracks[tracks['status'].isin(statuses)]
    if actor != 'Alle':
        shown = shown[shown['company']==actor]
    if search.strip():
        shown = shown[(shown['title']+' '+shown['company']).str.contains(search, case=False, regex=False)]
    st.dataframe(shown[['company','title','status','expected_decision_date']].rename(columns={
        'company':'Kunde', 'title':'Forretningsforløb', 'status':'Status', 'expected_decision_date':'Beslutningsdato'}),
        hide_index=True, use_container_width=True)
    if not len(shown):
        st.info('Ingen forløb matcher filtrene.')
        return
    ids = [int(x) for x in shown['id']]
    selected = st.selectbox('Åbn forretningsforløb', ids, format_func=lambda x:
        f"{shown.loc[shown['id']==x,'company'].iloc[0]} · {shown.loc[shown['id']==x,'title'].iloc[0]}", key='business_selected_track')
    row = shown.loc[shown['id']==selected].iloc[0].to_dict()
    st.markdown(f"### {row['company']} · {row['title']}")
    st.caption(f"{row['status']} · Beslutning: {date_text(row['expected_decision_date'])}")
    _followups(selected, 'selected_track')
    overview, proposals, engagements, deadlines, completed = st.tabs(['Pipeline','Tilbud','Kundeopgaver','Deadlines','Afsluttet'])
    with overview:
        st.write(row['need_description'] or 'Intet behov beskrevet.')
        with st.expander('Redigér forretningsforløb'):
            _track_editor(row, companies)
        with st.expander('Møder og opfølgningskoblinger'):
            _links(row)
    with proposals:
        _proposals(selected)
    with engagements:
        _engagements(selected)
    with deadlines:
        deliveries = q('''SELECT d.title, d.status, d.due_date, e.title AS engagement
            FROM deliverables d JOIN engagements e ON e.id=d.engagement_id
            WHERE e.track_id=? ORDER BY d.due_date, d.id''', (selected,))
        for _, delivery in deliveries.iterrows():
            st.write(f"**{delivery['title']}** · {delivery['status']} · {date_text(delivery['due_date'])}")
            st.caption(delivery['engagement'])
    with completed:
        for _, done in q("SELECT * FROM engagements WHERE track_id=? AND status IN ('Afsluttet','Annulleret')", (selected,)).iterrows():
            st.write(f"**{done['title']}** · {done['status']} · {date_text(done['completed_at'])}")
            st.write(done['outcome_notes'] or '')
            st.write(done['future_collaboration_note'] or '')
