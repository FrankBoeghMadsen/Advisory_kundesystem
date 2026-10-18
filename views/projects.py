import streamlit as st

from repositories import q
from services.project_service import (PROJECT_STATUSES, WORKSTREAM_STATUSES, ROLES,
    save_project, save_participant, save_workstream, link_track, remove_relation)
from ui.navigation import open_business


def _apply(action, *args):
    try:
        action(*args)
    except ValueError as exc:
        st.error(str(exc))
        return
    st.rerun()


def render():
    st.subheader('Projekter')
    with st.expander('Opret projekt'):
        with st.form('project_new', enter_to_submit=False):
            title=st.text_input('Projekttitel',key='project_new_title')
            purpose=st.text_area('Formål',key='project_new_purpose')
            status=st.selectbox('Projektstatus',PROJECT_STATUSES,key='project_new_status')
            if st.form_submit_button('Opret projekt'):
                try:
                    st.session_state['project_selected']=save_project(title,purpose,status)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    projects=q('SELECT * FROM projects ORDER BY updated_at DESC,id DESC')
    if projects.empty:
        st.info('Ingen projekter registreret.')
        return
    st.dataframe(projects[['title','status','purpose']].rename(columns={'title':'Projekt','status':'Status','purpose':'Formål'}),hide_index=True,use_container_width=True)
    ids=projects['id'].tolist()
    if st.session_state.get('project_selected') not in ids:
        st.session_state['project_selected']=ids[0]
    project_id=st.selectbox('Vælg projekt',ids,key='project_selected',
        format_func=lambda x: projects.loc[projects['id']==x,'title'].iloc[0])
    row=projects.loc[projects['id']==project_id].iloc[0]
    st.markdown('### '+row['title'])
    st.caption(row['status'])
    if row['purpose']:
        st.write(row['purpose'])
    with st.expander('Redigér projekt'):
        with st.form(f'project_edit_{project_id}',enter_to_submit=False):
            title=st.text_input('Projekttitel',row['title'])
            purpose=st.text_area('Formål',row['purpose'])
            status=st.selectbox('Projektstatus',PROJECT_STATUSES,index=PROJECT_STATUSES.index(row['status']))
            if st.form_submit_button('Gem projekt'):
                _apply(save_project,title,purpose,status,project_id)

    participants=q('SELECT p.*,c.name FROM project_companies p JOIN companies c ON c.id=p.company_id WHERE project_id=? ORDER BY c.name',(project_id,))
    st.markdown('#### Deltagende virksomheder')
    if participants.empty:
        st.caption('Ingen deltagere tilknyttet.')
    else:
        display=participants[['name']].rename(columns={'name':'Virksomhed'}).copy()
        display['Roller']=participants.apply(lambda r:', '.join(label for label,column in ROLES.items() if r[column]) or 'Ingen roller angivet',axis=1)
        st.dataframe(display,hide_index=True,use_container_width=True)
    companies=q('SELECT id,name FROM companies ORDER BY name')
    with st.expander('Tilføj / redigér deltager'):
        if companies.empty:
            st.info('Ingen virksomheder registreret.')
        else:
            company_id=st.selectbox('Virksomhed',companies['id'].tolist(),key=f'project_company_{project_id}',
                format_func=lambda x: companies.loc[companies['id']==x,'name'].iloc[0])
            member=participants.loc[participants['company_id']==company_id]
            selected=[label for label,column in ROLES.items() if not member.empty and member.iloc[0][column]]
            with st.form(f'project_member_{project_id}_{company_id}',enter_to_submit=False):
                roles=st.multiselect('Projektroller',list(ROLES),default=selected,key=f'project_roles_{project_id}_{company_id}')
                if st.form_submit_button('Gem deltager'):
                    _apply(save_participant,project_id,company_id,roles)
            if not member.empty:
                if st.button('Fjern deltager',key=f'project_remove_member_{project_id}_{company_id}'):
                    _apply(remove_relation,'participant',project_id,company_id)

    streams=q('SELECT w.*,c.name AS company FROM project_workstreams w LEFT JOIN companies c ON c.id=w.company_id WHERE project_id=? ORDER BY w.id',(project_id,))
    st.markdown('#### Faglige arbejdsspor')
    if streams.empty:
        st.caption('Ingen arbejdsspor registreret.')
    else:
        display=streams[['title','company','status']].copy()
        display['company']=display['company'].fillna('Fælles spor')
        st.dataframe(display.rename(columns={'title':'Arbejdsspor','company':'Virksomhed','status':'Status'}),hide_index=True,use_container_width=True)
    with st.expander('Opret / redigér arbejdsspor'):
        options=[None]+streams['id'].tolist()
        sid=st.selectbox('Arbejdsspor',options,key=f'project_stream_{project_id}',
            format_func=lambda x:'Nyt arbejdsspor' if x is None else streams.loc[streams['id']==x,'title'].iloc[0])
        current={} if sid is None else streams.loc[streams['id']==sid].iloc[0].to_dict()
        company_options=[None]+participants['company_id'].tolist()
        company=current.get('company_id')
        with st.form(f'project_stream_form_{project_id}_{sid}',enter_to_submit=False):
            title=st.text_input('Sportitel',current.get('title',''),key=f'project_stream_title_{project_id}_{sid}')
            company=st.selectbox('Virksomhed / fælles',company_options,index=company_options.index(company) if company in company_options else 0,
                format_func=lambda x:'Fælles spor' if x is None else participants.loc[participants['company_id']==x,'name'].iloc[0])
            status=st.selectbox('Sporstatus',WORKSTREAM_STATUSES,index=WORKSTREAM_STATUSES.index(current.get('status','Planlagt')))
            if st.form_submit_button('Gem arbejdsspor'):
                _apply(save_workstream,project_id,title,company,status,sid)
        if sid is not None:
            confirmed=st.checkbox('Bekræft sletning af arbejdsspor',key=f'project_delete_stream_confirm_{sid}')
            if st.button('Slet arbejdsspor',disabled=not confirmed,key=f'project_delete_stream_{sid}'):
                remove_relation('workstream',project_id,sid)
                st.session_state.pop(f'project_stream_{project_id}',None)
                st.rerun()

    st.markdown('#### Tilknyttede kommercielle forløb')
    linked=q('SELECT t.id,t.title,t.status,c.name FROM project_tracks p JOIN commercial_tracks t ON t.id=p.track_id JOIN companies c ON c.id=t.company_id WHERE p.project_id=? ORDER BY t.id',(project_id,))
    if linked.empty:
        st.caption('Ingen kommercielle forløb tilknyttet.')
    for _, track in linked.iterrows():
        a,b,c=st.columns([4,1,1])
        a.write(f"{track['name']} · {track['title']} · {track['status']}")
        if b.button('Åbn',key=f"project_open_track_{track['id']}"):
            open_business(int(track['id']))
            st.rerun()
        if c.button('Frakobl',key=f"project_unlink_track_{track['id']}"):
            _apply(remove_relation,'track',project_id,int(track['id']))
    with st.expander('Tilknyt eksisterende forløb'):
        candidates=q('''SELECT t.id,t.title,c.name FROM commercial_tracks t JOIN companies c ON c.id=t.company_id
            JOIN project_companies pc ON pc.company_id=t.company_id AND pc.project_id=?
            WHERE NOT EXISTS(SELECT 1 FROM project_tracks p WHERE p.track_id=t.id) ORDER BY c.name,t.title''',(project_id,))
        if candidates.empty:
            st.caption('Ingen ledige forløb hos projektdeltagerne.')
        else:
            with st.form(f'project_link_{project_id}',enter_to_submit=False):
                track_id=st.selectbox('Eksisterende forløb',candidates['id'].tolist(),
                    format_func=lambda x: candidates.loc[candidates['id']==x,'name'].iloc[0]+' · '+candidates.loc[candidates['id']==x,'title'].iloc[0])
                if st.form_submit_button('Tilknyt forløb'):
                    _apply(link_track,project_id,track_id)
