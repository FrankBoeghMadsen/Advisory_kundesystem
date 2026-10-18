import streamlit as st

from repositories import q
from services.project_service import (PROJECT_STATUSES, WORKSTREAM_STATUSES, ROLES,
    save_project, save_participant, save_workstream, link_track, remove_relation)
from ui.navigation import open_business


def _panel(kind=None, project_id=None, record_id=None):
    st.session_state['project_panel'] = dict(kind=kind, project_id=project_id, record_id=record_id)
    st.session_state['project_form_generation'] = st.session_state.get('project_form_generation',0)+1


def _open(kind, project_id=None, record_id=None):
    _panel(kind,project_id,record_id)
    st.rerun()


def _finish(message):
    _panel()
    st.session_state['project_receipt']=message
    st.rerun()


def _apply(action, *args, message):
    try:
        action(*args)
    except ValueError as exc:
        st.error(str(exc))
        return
    _finish(message)


def _cancel(prefix):
    if st.button('Annuller',key=prefix+'_cancel'):
        _open(None)


def stream_label(row):
    company=row.get('company')
    return f"{row['title']} · {company if isinstance(company,str) and company else 'Fælles spor'} · #{int(row['id'])}"


def render():
    with st.container(key='project_module'):
        _render()


def _render():
    st.subheader('Projekter')
    receipt=st.session_state.pop('project_receipt',None)
    if receipt:
        st.success(receipt)
    panel=st.session_state.get('project_panel',{})
    generation=st.session_state.get('project_form_generation',0)
    if st.button('Opret projekt',key='project_create_open'):
        _open('new_project')
    if panel.get('kind')=='new_project':
        prefix=f'project_new_{generation}'
        with st.form(prefix,enter_to_submit=False):
            title=st.text_input('Projekttitel',key=prefix+'_title')
            purpose=st.text_area('Formål',height=90,key=prefix+'_purpose')
            status=st.selectbox('Projektstatus',PROJECT_STATUSES,key=prefix+'_status')
            if st.form_submit_button('Opret projekt'):
                try:
                    project_id=save_project(title,purpose,status)
                    st.session_state['project_requested_selection']=project_id
                    _finish('Projektet er oprettet.')
                except ValueError as exc:
                    st.error(str(exc))
        _cancel(prefix)
    projects=q('SELECT * FROM projects ORDER BY updated_at DESC,id DESC')
    if projects.empty:
        st.info('Ingen projekter registreret.')
        return
    st.dataframe(projects[['title','status','purpose']].rename(columns={'title':'Projekt','status':'Status','purpose':'Formål'}),hide_index=True,use_container_width=True)
    ids=projects['id'].tolist()
    requested=st.session_state.pop('project_requested_selection',None)
    if requested in ids:
        st.session_state['project_selected']=requested
    if st.session_state.get('project_selected') not in ids:
        st.session_state['project_selected']=ids[0]
    project_id=st.selectbox('Vælg projekt',ids,key='project_selected',
        format_func=lambda x:f"{projects.loc[projects['id']==x,'title'].iloc[0]} · #{x}")
    if panel.get('project_id') is not None and panel['project_id']!=project_id:
        _panel()
        panel={}
    prefix=f"project_{panel.get('kind')}_{project_id}_{panel.get('record_id')}_{generation}"
    row=projects.loc[projects['id']==project_id].iloc[0]
    st.markdown('### '+row['title'])
    st.caption(row['status'])
    if row['purpose']:
        st.write(row['purpose'])
    if st.button('Redigér projekt',key=f'project_edit_open_{project_id}'):
        _open('edit_project',project_id)
    if panel.get('kind')=='edit_project':
        with st.form(prefix,enter_to_submit=False):
            title=st.text_input('Projekttitel',row['title'],key=prefix+'_title')
            purpose=st.text_area('Formål',row['purpose'],height=90)
            status=st.selectbox('Projektstatus',PROJECT_STATUSES,index=PROJECT_STATUSES.index(row['status']))
            if st.form_submit_button('Gem projekt'):
                _apply(save_project,title,purpose,status,project_id,message='Projektet er opdateret.')
        _cancel(prefix)

    participants=q('SELECT p.*,c.name FROM project_companies p JOIN companies c ON c.id=p.company_id WHERE project_id=? ORDER BY c.name',(project_id,))
    st.markdown('#### Deltagende virksomheder')
    if participants.empty:
        st.caption('Ingen deltagere tilknyttet.')
    for _, member in participants.iterrows():
        a,b=st.columns([5,1])
        a.write(member['name'])
        a.caption(', '.join(label for label,column in ROLES.items() if member[column]) or 'Ingen roller angivet')
        if b.button('Redigér',key=f"project_edit_member_{project_id}_{member['company_id']}"):
            _open('edit_member',project_id,int(member['company_id']))
    if st.button('Tilføj deltager',key=f'project_member_open_{project_id}'):
        _open('new_member',project_id)
    if panel.get('kind') in ('new_member','edit_member'):
        editing=panel['kind']=='edit_member'
        companies=q('SELECT id,name FROM companies ORDER BY name')
        available=companies[~companies['id'].isin(participants['company_id'])]
        member=participants.loc[participants['company_id']==panel.get('record_id')]
        if editing and member.empty:
            st.warning('Deltageren er ikke længere tilknyttet.')
        elif not editing and available.empty:
            st.info('Ingen nye virksomheder at tilføje.')
        else:
            with st.form(prefix,enter_to_submit=False):
                if editing:
                    company_id=int(member.iloc[0]['company_id'])
                    st.write(member.iloc[0]['name'])
                else:
                    company_id=st.selectbox('Virksomhed',available['id'].tolist(),index=None,placeholder='Vælg virksomhed',key=prefix+'_company',
                        format_func=lambda x:available.loc[available['id']==x,'name'].iloc[0])
                selected=[label for label,column in ROLES.items() if editing and member.iloc[0][column]]
                roles=st.multiselect('Projektroller',list(ROLES),default=selected,key=prefix+'_roles')
                if st.form_submit_button('Gem deltager'):
                    if company_id is None:
                        st.error('Vælg virksomhed.')
                    else:
                        _apply(save_participant,project_id,company_id,roles,message='Deltageren er opdateret.' if editing else 'Deltageren er tilknyttet projektet.')
            if editing:
                confirmed=st.checkbox('Bekræft fjernelse fra projektet. Virksomheden slettes ikke.',key=prefix+'_remove_confirm')
                if st.button('Fjern deltager fra projektet',disabled=not confirmed,key=prefix+'_remove'):
                    _apply(remove_relation,'participant',project_id,company_id,message='Deltageren er fjernet fra projektet. Virksomheden er ikke slettet.')
        _cancel(prefix)

    streams=q('SELECT w.*,c.name AS company FROM project_workstreams w LEFT JOIN companies c ON c.id=w.company_id WHERE project_id=? ORDER BY w.id',(project_id,))
    st.markdown('#### Faglige arbejdsspor')
    if streams.empty:
        st.caption('Ingen arbejdsspor registreret.')
    for _, stream in streams.iterrows():
        a,b,c=st.columns([4,1,1])
        a.write(stream_label(stream))
        b.caption(stream['status'])
        if c.button('Redigér',key=f"project_edit_stream_{stream['id']}"):
            _open('edit_stream',project_id,int(stream['id']))
    if st.button('Opret nyt arbejdsspor',key=f'project_stream_open_{project_id}'):
        _open('new_stream',project_id)
    if panel.get('kind') in ('new_stream','edit_stream'):
        editing=panel['kind']=='edit_stream'
        current_rows=streams.loc[streams['id']==panel.get('record_id')]
        if editing and current_rows.empty:
            st.warning('Arbejdssporet findes ikke længere.')
        else:
            current=current_rows.iloc[0].to_dict() if editing else {}
            if editing:
                st.write(stream_label(current))
            company_options=[None]+participants['company_id'].tolist()
            company=current.get('company_id')
            with st.form(prefix,enter_to_submit=False):
                title=st.text_input('Sportitel',current.get('title',''),key=prefix+'_title')
                company=st.selectbox('Virksomhed / fælles',company_options,index=company_options.index(company) if company in company_options else 0,
                    format_func=lambda x:'Fælles spor' if x is None else participants.loc[participants['company_id']==x,'name'].iloc[0],key=prefix+'_company')
                status=st.selectbox('Sporstatus',WORKSTREAM_STATUSES,index=WORKSTREAM_STATUSES.index(current.get('status','Planlagt')),key=prefix+'_status')
                if st.form_submit_button('Gem arbejdsspor'):
                    _apply(save_workstream,project_id,title,company,status,panel.get('record_id'),message='Arbejdssporet er opdateret.' if editing else 'Arbejdssporet er oprettet.')
            if editing:
                confirmed=st.checkbox('Bekræft sletning af arbejdsspor',key=prefix+'_delete_confirm')
                if st.button('Slet arbejdsspor',disabled=not confirmed,key=prefix+'_delete'):
                    _apply(remove_relation,'workstream',project_id,panel['record_id'],message='Arbejdssporet er slettet.')
        _cancel(prefix)

    st.markdown('#### Tilknyttede kommercielle forløb')
    linked=q('SELECT t.id,t.title,t.status,c.name FROM project_tracks p JOIN commercial_tracks t ON t.id=p.track_id JOIN companies c ON c.id=t.company_id WHERE p.project_id=? ORDER BY t.id',(project_id,))
    if linked.empty:
        st.caption('Ingen kommercielle forløb tilknyttet.')
    for _, track in linked.iterrows():
        a,b,c=st.columns([4,1,1])
        a.write(f"{track['name']} · {track['title']} · {track['status']}")
        if b.button('Åbn',key=f"project_open_track_{track['id']}"):
            _panel()
            open_business(int(track['id']),source_project=project_id)
            st.rerun()
        if c.button('Frakobl',key=f"project_unlink_track_{track['id']}"):
            _apply(remove_relation,'track',project_id,int(track['id']),message='Forretningsforløbet er frakoblet projektet. Selve forretningsforløbet er ikke slettet.')
    if st.button('Tilknyt eksisterende forløb',key=f'project_link_open_{project_id}'):
        _open('link_track',project_id)
    if panel.get('kind')=='link_track':
        candidates=q('''SELECT t.id,t.title,c.name FROM commercial_tracks t JOIN companies c ON c.id=t.company_id
            JOIN project_companies pc ON pc.company_id=t.company_id AND pc.project_id=?
            WHERE NOT EXISTS(SELECT 1 FROM project_tracks p WHERE p.track_id=t.id) ORDER BY c.name,t.title''',(project_id,))
        if candidates.empty:
            st.info('Ingen forretningsforløb kan tilknyttes endnu.\n\n'
                'Du kan tilknytte eksisterende forretningsforløb fra virksomheder, der er registreret som deltagere i projektet.\n\n'
                'Tilføj først den relevante virksomhed under Deltagende virksomheder, og opret om nødvendigt et forretningsforløb under Forretning → Forløb.')
        else:
            with st.form(prefix,enter_to_submit=False):
                track_id=st.selectbox('Eksisterende forløb',candidates['id'].tolist(),index=None,placeholder='Vælg forretningsforløb',key=prefix+'_track',
                    format_func=lambda x:f"{candidates.loc[candidates['id']==x,'name'].iloc[0]} · {candidates.loc[candidates['id']==x,'title'].iloc[0]} · #{x}")
                if st.form_submit_button('Tilknyt forløb'):
                    if track_id is None:
                        st.error('Vælg forretningsforløb.')
                    else:
                        _apply(link_track,project_id,track_id,message='Forretningsforløbet er tilknyttet projektet.')
        _cancel(prefix)
