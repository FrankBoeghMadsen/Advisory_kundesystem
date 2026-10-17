import streamlit as st

NAV_GROUPS = {
    'DAGLIGT ARBEJDE': {
        'Dashboard':['Dashboard'], 'Forretning':['Forretning'],
        'Møder og opfølgninger':['Møder','Opgaver'],
        'Kontakter og virksomheder':['Kontakter','Virksomheder']},
    'VIDEN OG MULIGHEDER': {
        'Observationer':['Observationer'], 'Viden':['Viden'],
        'Regulatorisk overvågning':['Signalindbakke','Kilder','Triggerregler','Briefing']}}


def render_navigation():
    page = st.session_state.get('page','Dashboard')
    for heading, groups in NAV_GROUPS.items():
        st.caption(heading)
        for label, pages in groups.items():
            if st.button(label, key='nav_'+label, use_container_width=True,
                         type='primary' if page in pages else 'secondary'):
                st.session_state.pop('record_focus',None)
                st.session_state.pop('business_listing',None)
                st.session_state.pop('business_focus',None)
                set_page(pages[0])
                st.rerun()
    pages = next(pages for groups in NAV_GROUPS.values() for pages in groups.values() if page in pages)
    if len(pages)>1:
        chosen = st.radio('Visning', pages, index=pages.index(page), horizontal=True,
                          format_func=lambda p:'Opfølgninger' if p=='Opgaver' else p)
        if chosen != page:
            set_page(chosen)
            st.rerun()


def open_business(track_id, section='Pipeline', record_id=None, kind=None):
    st.session_state['business_track_id'] = int(track_id)
    st.session_state['business_requested_section'] = section
    st.session_state['business_focus'] = dict(kind=kind, id=record_id,track_id=int(track_id))
    st.session_state.pop('business_listing',None)
    set_page('Forretning')


def open_activity(item):
    kind = item['kind']
    if kind in ('Møde','Opfølgning'):
        page = 'Møder' if kind=='Møde' else 'Opgaver'
        st.session_state['record_focus'] = dict(page=page,id=int(item['id']))
        set_page(page)
    elif kind == 'Leverancefrist':
        open_business(item['track_id'],'Kundeopgaver',int(item['id']),'deliverable')
    elif kind == 'Tilbudsfrist':
        open_business(item['track_id'],'Tilbud',int(item['id']),'proposal')
    else:
        open_business(item['id'])


def set_page(name):
    st.session_state["page"] = name


def set_company(company_id):
    st.session_state["selected_company_id"] = int(company_id)
    st.session_state["force_profile_view"] = True


def open_company_section(company_id, section):
    st.session_state["selected_company_id"] = int(company_id)
    st.session_state[f"profile_section_{int(company_id)}"] = section
    st.session_state["force_profile_view"] = True
    st.session_state["page"] = "Virksomheder"


def open_followup(company_id, followup_id):
    st.session_state["highlight_followup_id"] = int(followup_id)
    open_company_section(company_id, "Opfølgning")
