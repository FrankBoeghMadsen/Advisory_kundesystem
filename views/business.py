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
    set_track_followups, set_deliverable_followups, accept_amendment, document_legacy_acceptance)
from services.activity_service import dashboard_data, ACTIVE_ENGAGEMENTS
from ui.navigation import open_business, open_activity, open_company_section
from services.business_values import (clean, number_text, parse_danish_number,
                                      fee_text, parse_date, date_text, iso_date, timestamp_text)

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
    return {key: parse_danish_number(value,allow_currency=key not in ('max_hours','included_hours')) if key not in ('fee_model', 'fee_note') else value
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
        if st.button('Redigér opfølgning', key=f"{prefix}_open_{item['id']}"):
            open_activity(dict(kind='Opfølgning',id=int(item['id'])))
            st.rerun()
    if st.button('Åbn opfølgninger', key=prefix+'_followups'):
        st.session_state['page'] = 'Opgaver'
        st.rerun()
    with st.expander('Afsluttede opfølgninger'):
        closed = q("SELECT * FROM followups WHERE commercial_track_id=? AND status IN ('Lukket','Arkiveret') ORDER BY completed_at DESC,id DESC", (track_id,))
        if not len(closed):
            st.caption('Ingen afsluttede opfølgninger tilknyttet.')
        for _, item in closed.iterrows():
            st.write('**'+item['title']+'**')
            st.caption(item['status']+' · '+(timestamp_text(item['completed_at']) if item['completed_at'] else 'Afslutningsdato ikke registreret'))
            if item['completion_result']:
                st.write(item['completion_result'])
            if st.button('Åbn', key=f"{prefix}_closed_{item['id']}"):
                open_activity(dict(kind='Opfølgning', id=int(item['id'])))
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
    selected = st.multiselect('Møder', ids, default=[int(x) for x in linked['meeting_id'] if x in ids], placeholder='Vælg møder',
        format_func=lambda x: f"{date_text(meetings.loc[meetings['id']==x,'meeting_date'].iloc[0])} · {meetings.loc[meetings['id']==x,'title'].iloc[0]}", key=f'meeting_links_{track_id}') if ids else []
    if not ids:
        st.caption('Ingen møder registreret.')
    if st.button('Gem mødekoblinger', key=f'save_meetings_{track_id}'):
        set_track_meetings(track_id, selected)
        st.rerun()
    followups = q('SELECT id, title FROM followups WHERE company_id=? ORDER BY created_at DESC', (company_id,))
    linked_f = q('SELECT id FROM followups WHERE commercial_track_id=?', (track_id,))
    ids_f = [int(x) for x in followups['id']]
    selected_f = st.multiselect('Opfølgninger', ids_f, default=[int(x) for x in linked_f['id'] if x in ids_f], placeholder='Vælg opfølgninger',
        format_func=lambda x: followups.loc[followups['id']==x, 'title'].iloc[0], key=f'follow_links_{track_id}') if ids_f else []
    if not ids_f:
        st.caption('Ingen opfølgninger registreret.')
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
    fees = _fees(prefix, row, agreed=True) if not row.get('id') else {}
    if st.button('Accepter tilbud og opret kundeopgave' if proposal else 'Gem kundeopgave', key=prefix+'_save', type='primary'):
        try:
            parsed = _parsed_fees(fees)
            if not title.strip():
                raise ValueError('Opgavetitel skal udfyldes.')
            if proposal:
                created_id = create_engagement_from_proposal(int(proposal['id']), title, description, status,
                    iso_date(start), iso_date(end), parsed['fee_model'], parsed['agreed_fee_ex_vat'],
                    parsed['fee_note'], parsed.get('max_hours'), parsed.get('fee_cap_ex_vat'), parsed.get('included_hours'))
                save_business_record('engagements', dict(title=title, completed_at=iso_date(completed)), created_id)
                st.rerun()
            else:
                _save('engagements', dict(track_id=track_id, title=title, description=description,
                    status=status, start_date=iso_date(start), target_end_date=iso_date(end), completed_at=iso_date(completed),
                    **parsed), row.get('id'))
        except ValueError as exc:
            st.error(str(exc))


def _fee_details(row, agreed=False):
    label='Aktuelt aftalt honorar' if agreed else row['fee_model']
    st.write(f"**{label}:** {fee_text(row['agreed_fee_ex_vat' if agreed else 'offered_fee_ex_vat'], row['fee_model'])}")
    if agreed:
        st.caption(row['fee_model'])
    for key, label in [('max_hours','Aftalt timeloft'),('fee_cap_ex_vat','Honorarloft ekskl. moms'),('included_hours','Inkluderede timer')]:
        if clean(row.get(key)) is not None:
            st.caption(f'{label}: {number_text(row[key])}')
    if row.get('fee_note'):
        st.write(row['fee_note'])


def _proposals(track_id):
    with st.expander('Opret tilbud'):
        _proposal_editor({}, track_id)
    rows = q('SELECT * FROM proposals WHERE track_id=? ORDER BY version DESC', (track_id,))
    focus=st.session_state.get('business_focus',{})
    if focus.get('kind')=='proposal':
        rows=rows[rows['id']==focus['id']]
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
                        st.write(f"{timestamp_text(log['changed_at'])} · {log['reason']}")
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
    rows=q('SELECT * FROM engagements WHERE track_id=? ORDER BY created_at DESC', (track_id,))
    focus=st.session_state.get('business_focus',{})
    if focus.get('kind')=='engagement':
        rows=rows[rows['id']==focus['id']]
    elif focus.get('kind')=='deliverable':
        parent=q('SELECT engagement_id FROM deliverables WHERE id=?',(focus['id'],))
        rows=rows[rows['id'].isin(parent['engagement_id'].tolist())]
    for _, series in rows.iterrows():
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
                if row['accepted_proposal_snapshot']:
                    accepted=json.loads(row['accepted_proposal_snapshot'])
                    st.markdown('**Tilbud ved accept**')
                    st.write(accepted.get('scope') or accepted.get('title',''))
                    st.write(fee_text(accepted.get('offered_fee_ex_vat'),accepted.get('fee_model','Fast pris')))
                else:
                    st.caption('Tilbudsversion ved accept er ikke særskilt registreret historisk.')
            with st.expander('Aftaleændringer'):
                for _, amendment in q('SELECT * FROM engagement_amendments WHERE engagement_id=? ORDER BY id DESC', (eid,)).iterrows():
                    st.write(f"**{date_text(amendment['amendment_date'])}** · {amendment['description']}")
                    st.caption(amendment['status'] if amendment['status']!='Historisk registreret' else 'Tidligere registreret – acceptstatus ikke registreret')
                    if amendment['accepted_at']:
                        st.caption(f"Registreret: {timestamp_text(amendment['accepted_at'])}")
                    if clean(amendment['new_fee']) is not None:
                        st.caption(f"Honorar: {number_text(amendment['previous_fee']) or 'Ikke registreret'} → {number_text(amendment['new_fee'])}")
                    st.write(amendment['acceptance_reference'] or 'Dokumentationsgrundlag ikke angivet.')
                    changed_terms=json.loads(amendment['proposed_terms'] or '{}')
                    if changed_terms:
                        st.table([{'Vilkår':FIELD_LABELS.get(k,'Aftalt honorar' if k=='agreed_fee_ex_vat' else k),
                            'Ny værdi':(number_text(v) if isinstance(v,(int,float)) else str(v)) if v is not None else 'Ikke registreret'} for k,v in changed_terms.items()])
                    accept_ref=None
                    if amendment['status']=='Foreslået':
                        accept_ref=st.text_input('Acceptreference (mail, møde eller mundtlig aftale)',amendment['acceptance_reference'] or '',key=f"accept_ref_{amendment['id']}")
                    if amendment['status']=='Foreslået' and st.button('Registrér kundens accept',key=f"accept_amendment_{amendment['id']}"):
                        try:
                            accept_amendment(int(amendment['id']),accept_ref)
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                    if amendment['status']=='Historisk registreret':
                        legacy_ref=st.text_input('Dokumentér historisk accept',amendment['acceptance_reference'] or '',key=f"legacy_ref_{amendment['id']}")
                        if st.button('Gem historisk acceptreference',key=f"legacy_save_{amendment['id']}"):
                            try:
                                document_legacy_acceptance(int(amendment['id']),legacy_ref)
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))
                day = _date('Ændringsdato', None, f'amendment_day_{eid}')
                description = st.text_area('Beskrivelse af aftaleændring', key=f'amendment_desc_{eid}')
                new_fee = _number('Nyt aftalt honorar ekskl. moms', None, f'amendment_fee_{eid}')
                reference = st.text_input('Reference til kundens accept / dokumentation', key=f'amendment_ref_{eid}')
                amendment_status=st.radio('Aftalestatus',['Foreslået','Accepteret'],key=f'amendment_status_{eid}',horizontal=True)
                terms={}
                if st.checkbox('Ændr honorarmodel eller øvrige honorarvilkår',key=f'amendment_terms_{eid}'):
                    parsed_source=_fees(f'amendment_terms_{eid}',row,agreed=True)
                    terms=parsed_source
                if st.button('Registrér aftaleændring', key=f'amendment_save_{eid}'):
                    try:
                        parsed_terms=_parsed_fees(terms) if terms else {}
                        record_amendment(eid, iso_date(day), description, reference,
                            parse_danish_number(new_fee,allow_currency=True),amendment_status,parsed_terms)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            with st.expander('Evaluering'):
                actual=_number('Faktisk anvendte timer',row['actual_hours'],f'eval_hours_{eid}')
                reuse=_select('Genanvendelsespotentiale',['Ikke vurderet','Ja','Nej'],row['reuse_potential'],f'eval_reuse_{eid}')
                notes=st.text_area('Genanvendelig viden, metoder og værktøjer',row['reuse_notes'] or '',key=f'eval_notes_{eid}')
                outcome=st.text_area('Resultat og læring',row['outcome_notes'] or '',key=f'eval_outcome_{eid}')
                future=st.text_area('Muligt fremtidigt samarbejde',row['future_collaboration_note'] or '',key=f'eval_future_{eid}')
                if st.button('Gem evaluering',key=f'eval_save_{eid}'):
                    try:
                        _save('engagements',dict(title=row['title'],actual_hours=parse_danish_number(actual),
                            reuse_potential=reuse,reuse_notes=notes,outcome_notes=outcome,future_collaboration_note=future),eid)
                    except ValueError as exc:
                        st.error(str(exc))
            st.markdown('**Leverancer**')
            for _, delivery_series in q('SELECT * FROM deliverables WHERE engagement_id=? ORDER BY due_date, id', (eid,)).iterrows():
                delivery = delivery_series.to_dict()
                if focus.get('kind')=='deliverable' and int(delivery['id'])!=focus.get('id'):
                    continue
                st.write(f"{delivery['title']} · {delivery['status']} · {date_text(delivery['due_date'])}")
                with st.expander(f"Redigér leverance: {delivery['title']}",expanded=focus.get('kind')=='deliverable'):
                    _deliverable_editor(delivery, eid)
                    candidates = q('SELECT id, title FROM followups WHERE company_id=(SELECT company_id FROM commercial_tracks WHERE id=?)', (track_id,))
                    linked = q('SELECT id FROM followups WHERE deliverable_id=?', (int(delivery['id']),))
                    ids = [int(x) for x in candidates['id']]
                    chosen = st.multiselect('Opfølgninger til leverancen', ids, default=[int(x) for x in linked['id'] if x in ids], placeholder='Vælg opfølgninger',
                        format_func=lambda x: candidates.loc[candidates['id']==x,'title'].iloc[0], key=f"delivery_links_{delivery['id']}") if ids else []
                    if not ids:
                        st.caption('Ingen opfølgninger registreret.')
                    if st.button('Gem leverancekoblinger', key=f"delivery_link_save_{delivery['id']}"):
                        set_deliverable_followups(int(delivery['id']), chosen)
                        st.rerun()
            with st.expander('Opret leverance'):
                _deliverable_editor({}, eid)


def _render_listing(label):
    rows=dashboard_data()['groups'].get(label,[])
    st.markdown(f'### {label} ({len(rows)})')
    for row in rows:
        cols=st.columns([5,1])
        cols[0].write(f"**{row['company'] or 'Ingen aktør'}** · {row['title']} · {row.get('status','')}")
        if cols[1].button('Åbn',key=f"listing_{label}_{row['id']}"):
            if label=='Aktive kunder':
                st.session_state.pop('business_listing',None)
                open_company_section(row['company_id'],'Forretning')
            elif label=='Åbne opfølgninger':
                open_activity(dict(row,kind='Opfølgning'))
            elif label=='Åbne leverancer':
                open_activity(dict(row,kind='Leverancefrist'))
            elif label=='Tilbud afventer svar':
                open_activity(dict(row,kind='Tilbudsfrist'))
            elif label=='Aktive kundeopgaver':
                open_business(row['track_id'],'Kundeopgaver',int(row['id']),'engagement')
            else:
                open_business(row['id'])
            st.rerun()
    if not rows:
        st.caption('Ingen registreringer i oversigten.')
    if st.button('Alle forretningsforløb',key='leave_listing'):
        st.session_state.pop('business_listing',None)
        st.rerun()


def render():
    st.subheader('Forretning')
    if st.session_state.get('business_listing'):
        _render_listing(st.session_state['business_listing'])
        return
    requested=st.session_state.pop('business_requested_view',None)
    if requested:
        st.session_state['business_view']=requested
    view=st.radio('Forretningsvisning',['Forløb','Projekter'],horizontal=True,key='business_view')
    if view=='Projekter':
        from views.projects import render as render_projects
        render_projects()
        return
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
    if 'business_status_filter' not in st.session_state:
        st.session_state['business_status_filter']=TRACK_STATUSES
    with st.container(key='business_status_filters'):
        statuses = st.multiselect('Status på forløb', TRACK_STATUSES,
            default=None, key='business_status_filter')
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
    if st.session_state.get('business_focus',{}).get('track_id',selected)!=selected:
        st.session_state.pop('business_focus',None)
    st.markdown(f"### {row['company']} · {row['title']}")
    st.caption(f"{row['status']} · Beslutning: {date_text(row['expected_decision_date'])}")
    _followups(selected, 'selected_track')
    counts={
        'Tilbud':int(q('SELECT COUNT(*) AS n FROM proposals WHERE track_id=?',(selected,)).iloc[0]['n']),
        'Kundeopgaver':int(q('SELECT COUNT(*) AS n FROM engagements WHERE track_id=?',(selected,)).iloc[0]['n']),
        'Afsluttet':int(q("SELECT COUNT(*) AS n FROM engagements WHERE track_id=? AND status IN ('Afsluttet','Annulleret')",(selected,)).iloc[0]['n'])}
    deliveries=q('''SELECT d.*, e.title AS engagement, e.track_id FROM deliverables d
        JOIN engagements e ON e.id=d.engagement_id WHERE e.track_id=?
        AND d.status NOT IN ('Leveret','Annulleret') AND e.status IN ('Planlagt','I gang','Afventer')
        ORDER BY d.due_date,d.id''',(selected,))
    deliveries=deliveries[deliveries['due_date'].apply(lambda value:parse_date(value) is not None)]
    counts['Deadlines']=len(deliveries)
    if st.session_state.get('business_focus',{}).get('id'):
        if st.button('Vis hele forløbet',key='clear_business_focus'):
            st.session_state.pop('business_focus',None)
            st.rerun()
    st.divider()
    sections=['Pipeline','Tilbud','Kundeopgaver','Deadlines','Afsluttet']
    requested_section=st.session_state.pop('business_requested_section',None)
    with st.container(key='business_navigation'):
        section=st.radio('Forretningsområde',sections,
            index=sections.index(requested_section or st.session_state.get('business_section','Pipeline')),
            horizontal=True,key='business_section',format_func=lambda name:f'{name} ({counts[name]})' if name in counts else name)
    st.divider()
    if section=='Pipeline':
        st.write(row['need_description'] or 'Intet behov beskrevet.')
        with st.expander('Redigér forretningsforløb'):
            _track_editor(row, companies)
        with st.expander('Møder og opfølgningskoblinger'):
            _links(row)
    elif section=='Tilbud':
        _proposals(selected)
    elif section=='Kundeopgaver':
        _engagements(selected)
    elif section=='Deadlines':
        for _, delivery in deliveries.iterrows():
            st.write(f"**{delivery['title']}** · {delivery['status']} · {date_text(delivery['due_date'])}")
            st.caption(delivery['engagement'])
            if st.button('Åbn leverance',key=f"deadline_open_{delivery['id']}"):
                open_activity(dict(delivery,kind='Leverancefrist'))
                st.rerun()
    elif section=='Afsluttet':
        for _, done in q("SELECT * FROM engagements WHERE track_id=? AND status IN ('Afsluttet','Annulleret')", (selected,)).iterrows():
            st.write(f"**{done['title']}** · {done['status']} · {date_text(done['completed_at'])}")
            st.write(done['outcome_notes'] or '')
            st.write(done['future_collaboration_note'] or '')
