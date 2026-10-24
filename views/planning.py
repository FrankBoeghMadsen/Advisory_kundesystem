from datetime import timedelta

import streamlit as st

from repositories import q
from services.business_values import clean
from services.planning_service import (DAYS, local_today, week_data, planning_targets,
    save_work_block, delete_work_block, set_capacity)
from ui.navigation import open_activity, open_business


def hours(value):
    return f'{value/60:g}'.replace('.',',')


def _shift(days):
    st.session_state['planning_week_picker']=(st.session_state.get('planning_week_picker') or local_today())+timedelta(days=days)


def _finish(message):
    st.session_state['planning_editor']=None
    st.session_state['planning_generation']=st.session_state.get('planning_generation',0)+1
    st.session_state['planning_receipt']=message
    st.rerun()


def render():
    st.subheader('Ugeplan')
    receipt=st.empty()
    message=st.session_state.pop('planning_receipt',None)
    if message:
        receipt.success(message)
    prev,now,nxt=st.columns(3)
    prev.button('Forrige uge',icon=':material/chevron_left:',on_click=_shift,args=(-7,))
    if now.button('Denne uge'):
        st.session_state['planning_week_picker']=local_today()
        st.rerun()
    nxt.button('Næste uge',icon=':material/chevron_right:',on_click=_shift,args=(7,))
    selected=st.date_input('Dato i den ønskede uge',value=local_today(),key='planning_week_picker',format='DD-MM-YYYY')
    if selected is None:
        st.info('Vælg en dato for at vise ugen.')
        return
    data=week_data(selected)
    st.write(f"**Uge {data['start'].isocalendar().week} · {data['start']:%d-%m-%Y} – {data['days'][-1]['day']:%d-%m-%Y}**")
    st.caption(f"{hours(data['planned'])} af {hours(data['capacity'])} timer planlagt · netto {hours(data['remaining'])} timer tilbage")
    warning_slot=st.empty()
    if any(d['remaining']<0 for d in data['days']):
        warning_slot.warning('En eller flere dage er over kapacitet. Planlægningen er gemt; se de enkelte dage.')
    with st.container(key='week_calendar'):
        columns=st.columns(7)
    for col,day in zip(columns,data['days']):
        with col:
            st.markdown(f"**{DAYS[day['day'].weekday()]} {day['day']:%d/%m}**"+(' · I dag' if day['day']==local_today() else ''))
            st.caption(f"{hours(day['planned'])} af {hours(day['capacity'])} t planlagt")
            if day['remaining']<0:
                st.error(f"{hours(-day['remaining'])} t over kapacitet")
            else:
                st.caption(f"{hours(day['remaining'])} t ledige")
            for block in day['blocks']:
                st.write(f"{hours(block['planned_minutes'])} t · {block['description']}")
                st.caption(block['company'])
                if block in day['after_deadline']:
                    st.warning('Planlagt efter leverancens deadline')
                if st.button('Redigér',key=f"plan_edit_{block['id']}"):
                    st.session_state['planning_editor']=int(block['id'])
                    st.session_state['planning_generation']=st.session_state.get('planning_generation',0)+1
                    st.rerun()
            for delivery in day['deadlines']:
                overdue=day['day']<local_today()
                (st.error if overdue else st.info)(('Overskredet leverancefrist: ' if overdue else 'Leverancefrist: ')+delivery['title'])
                if st.button('Åbn leverance',key=f"plan_deadline_{delivery['id']}"):
                    open_activity(dict(delivery,kind='Leverancefrist'))
                    st.rerun()
    if st.button('Opret arbejdsblok',icon=':material/add:',key='plan_new'):
        st.session_state['planning_editor']='new'
        st.session_state['planning_generation']=st.session_state.get('planning_generation',0)+1
        st.rerun()
    slot=st.empty()
    editor=st.session_state.get('planning_editor')
    if editor:
        with slot.container():
            _editor(editor,data['start'])
    with st.expander('Dagskapacitet'):
        capacity_day=st.date_input('Kapacitetsdato',value=selected,key='capacity_day',format='DD-MM-YYYY')
        if capacity_day is None:
            st.info('Vælg en kapacitetsdato.')
            return
        existing=q('SELECT capacity_minutes FROM daily_capacity WHERE work_date=?',(capacity_day.isoformat(),))
        default=float(existing.iloc[0]['capacity_minutes'])/60 if len(existing) else (7.0 if capacity_day.weekday()<5 else 0.0)
        with st.form('capacity_form_'+capacity_day.isoformat(),enter_to_submit=False):
            capacity=st.number_input('Disponible timer',min_value=0.0,value=default,step=0.25,key='capacity_hours_'+capacity_day.isoformat())
            if st.form_submit_button('Gem dagskapacitet'):
                try:
                    set_capacity(capacity_day,capacity)
                    _finish('Dagskapaciteten er gemt.')
                except ValueError as exc:
                    st.error(str(exc))


def _editor(editor, default_day):
    targets=planning_targets()
    labels={ (int(r['engagement_id']),int(clean(r['deliverable_id'])) if clean(r['deliverable_id']) is not None else None):
            f"{r['company']} · {'Leverance' if clean(r['deliverable_id']) is not None else 'Kundeopgave'} · {r['title']} · #{int(clean(r['deliverable_id']) or r['engagement_id'])}" for r in targets }
    current={}
    if editor!='new':
        rows=q('SELECT * FROM work_blocks WHERE id=?',(editor,))
        if rows.empty:
            st.warning('Arbejdsblokken findes ikke længere.')
            return
        current=rows.iloc[0].to_dict()
    from services.business_values import parse_date
    chosen=(int(current['engagement_id']),clean(current.get('deliverable_id'))) if current else None
    prefix=f"work_block_{editor}_{st.session_state.get('planning_generation',0)}"
    with st.form(prefix,enter_to_submit=False):
        day=st.date_input('Arbejdsdato',value=parse_date(current.get('work_date')) or default_day,format='DD-MM-YYYY')
        options=list(labels)
        target=st.selectbox('Kundeopgave eller leverance',options,index=options.index(chosen) if chosen in options else None,
                            placeholder='Vælg kundeopgave eller leverance',format_func=labels.get,key=prefix+'_target')
        description=st.text_input('Kort beskrivelse',current.get('description',''),key=prefix+'_description')
        amount=st.number_input('Planlagte timer',min_value=0.0,value=float(current.get('planned_minutes',60))/60,step=0.25,key=prefix+'_hours')
        note=st.text_area('Planlægningsnote',current.get('note',''),height=80,key=prefix+'_note')
        a,b=st.columns(2)
        save=a.form_submit_button('Gem arbejdsblok')
        cancel=b.form_submit_button('Annuller')
        if cancel:
            _finish('Ingen ændringer gemt.')
        if save:
            try:
                if target is None:
                    raise ValueError('Vælg kundeopgave eller leverance.')
                save_work_block(day,*target,description,amount,note,current.get('id'))
                _finish('Arbejdsblokken er gemt.')
            except ValueError as exc:
                st.error(str(exc))
    if current:
        if st.button('Åbn kundeopgave',key=prefix+'_open'):
            parent=q('SELECT track_id FROM engagements WHERE id=?',(current['engagement_id'],)).iloc[0]
            open_business(int(parent['track_id']),'Kundeopgaver',int(current['engagement_id']),'engagement')
            st.rerun()
        confirmed=st.checkbox('Bekræft sletning af arbejdsblokken',key=prefix+'_confirm')
        if st.button('Slet arbejdsblok',disabled=not confirmed,key=prefix+'_delete'):
            delete_work_block(int(current['id']))
            _finish('Arbejdsblokken er slettet. Kundeopgave og leverance er bevaret.')
