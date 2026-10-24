import streamlit as st

from services.activity_service import dashboard_data, activity_urgency
from services.planning_service import local_today, danish_date
from services.business_values import date_text, clean
from ui.navigation import open_activity, open_business, set_page


def render():
    today=local_today()
    st.subheader(danish_date(today))
    mode=st.radio('Dashboardvisning',['Overblik','Ugeplan'],horizontal=True,key='dashboard_view')
    if mode=='Ugeplan':
        from views.planning import render as render_planning
        render_planning()
        return
    data = dashboard_data(today)
    st.subheader('Aktiviteter og deadlines')
    st.caption(f"{data['overdue']} passerede datoer · {data['next30']} aktiviteter i dag og de næste 30 dage")
    if not data['activities']:
        st.caption('Ingen daterede aktiviteter kræver opmærksomhed i perioden.')
    for item in data['activities']:
        with st.container(key=f"dashboard_activity_{item['kind']}_{item['id']}"):
            label = date_text(item['day'])
            dates,a,b = st.columns([2,6,1])
            state,tone=activity_urgency(item,today)
            dates.markdown(f':{tone}[**{label}**]' if tone!='neutral' else f'**{label}**')
            if state:
                dates.caption(state)
            if item.get('meeting_time'):
                dates.caption('Kl. '+item['meeting_time'])
            a.markdown(f"**{item.get('company') or 'Ingen aktør'} · {item['title']}**")
            meta = f"{item['kind']} · {item.get('status') or 'Planlagt'}"
            if not item['binding']:
                meta += ' · forventning, ikke bindende deadline'
            if item.get('priority'):
                meta += f" · {'**Høj prioritet**' if item['priority']=='Høj' else item['priority']+' prioritet'}"
            a.caption(meta)
            if item['related_followups']:
                a.caption(f"{len(item['related_followups'])} tilknyttet opfølgning på samme frist")
                with st.expander('Tilknyttede opfølgninger'):
                    for related in item['related_followups']:
                        st.write(related['title'])
                        if st.button('Åbn opfølgning',key=f"related_followup_{related['id']}"):
                            open_activity(dict(related,kind='Opfølgning'))
                            st.rerun()
            if b.button('Åbn',key=f"activity_{item['kind']}_{item['id']}",use_container_width=True):
                open_activity(item)
                st.rerun()

    st.markdown('### Arbejdsoversigter')
    columns = st.columns(3)
    for index,(label,rows) in enumerate(data['groups'].items()):
        if columns[index%3].button(f'{label} · {len(rows)}',key='kpi_'+label,use_container_width=True):
            st.session_state['business_listing'] = label
            set_page('Forretning')
            st.rerun()

    st.markdown('### Kunder og næste skridt')
    for task in data['engagements'][:5]:
        cols=st.columns([5,1])
        cols[0].write(f"**{task['company']}** · {task['title']} · {task['status']}")
        if cols[1].button('Åbn',key=f"customer_task_{task['id']}"):
            open_business(task['track_id'],'Kundeopgaver',int(task['id']),'engagement')
            st.rerun()
    with st.expander('Tilbud og muligheder'):
        for row in data['proposals'][:5]:
            st.write(f"{row['company']} · {row['title']} · {row['status']}")
        for row in data['tracks'][:5]:
            st.write(f"{row['company']} · {row['title']}")
            related = [f for f in data['followups'] if clean(f.get('commercial_track_id'))==row['id']]
            for followup in related[:1]:
                st.caption(f"{followup.get('next_action') or followup['title']} · {date_text(followup.get('due_date'))}")
    if data['undated'] or data['rest_deliveries']:
        with st.expander('Udaterede aktiviteter og åbne restleverancer'):
            for row in data['rest_deliveries']:
                st.write(f"{row['company']} · {row['title']} · kundeopgave {row['engagement_status']}")
                if st.button('Åbn restleverance',key=f"rest_{row['id']}"):
                    open_activity(dict(row,kind='Leverancefrist'))
                    st.rerun()
            for row in data['undated']:
                st.caption(f"{row.get('company') or 'Ingen aktør'} · {row['title']} · {row['date_value'] or 'Ingen dato'}")
