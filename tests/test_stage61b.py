import unittest

from tests import test_stage61a


class Stage61bTests(unittest.TestCase):
    run_ui=test_stage61a.Stage61aTests.run_ui

    def test_contextual_link_guidance_and_no_view_writes(self):
        self.run_ui('''
p=save_project('TEST Vejledning')
app=start(p)
assert any(x.value=='TESTDATABASE' for x in app.sidebar.warning)
assert any(x.label=='Om og tekniske oplysninger' for x in app.sidebar.expander)
before=list(conn.iterdump())
app.button(key=f'project_link_open_{p}').click().run()
assert any('ingen deltagende virksomheder' in x.value for x in app.info)
assert list(conn.iterdump())==before
field(app,'button','Annuller').click().run()
save_participant(p,b,['Deltager'])
app.button(key=f'project_link_open_{p}').click().run()
assert any('TEST Beta' in x.value and 'ingen eksisterende kommercielle forløb' in x.value for x in app.info)
field(app,'button','Annuller').click().run()
save_participant(p,a,['Koordinator'])
app.button(key=f'project_link_open_{p}').click().run()
assert field(app,'selectbox','Eksisterende forløb').value is None
assert any('Der oprettes ikke et nyt forløb' in x.value for x in app.caption)
field(app,'button','Annuller').click().run()
link_track(p,track)
app.button(key=f'project_link_open_{p}').click().run()
assert any('1 forløb er allerede tilknyttet dette projekt.' in x.value for x in app.info)
field(app,'button','Annuller').click().run()
other=save_project('TEST Andet projekt')
save_participant(other,a,['Deltager'])
app.run()
app.selectbox(key='project_selected').select(other).run()
before=list(conn.iterdump())
app.button(key=f'project_link_open_{other}').click().run()
assert any('1 forløb er allerede tilknyttet andre projekter.' in x.value for x in app.info)
assert not any(x.label=='Eksisterende forløb' for x in app.selectbox)
assert list(conn.iterdump())==before
conn.close()
''')

    def test_cancel_does_not_save_and_return_context_is_validated(self):
        self.run_ui('''
p=save_project('TEST Handlinger')
save_participant(p,a,['Koordinator'])
s=save_workstream(p,'TEST Bevar spor',a)
link_track(p,track)
app=start(p)
before=list(conn.iterdump())
for opener,label in [('project_create_open','Projekttitel'),
    (f'project_edit_open_{p}','Projekttitel'),
    (f'project_stream_open_{p}','Sportitel'),
    (f'project_edit_stream_{s}','Sportitel')]:
    app.button(key=opener).click().run()
    field(app,'text_input',label).set_value('TEST Må ikke gemmes')
    assert len([x for x in app.button if x.label=='Annuller'])==1
    field(app,'button','Annuller').click().run()
    assert not len(app.exception),list(app.exception)
    readonly(app)
    assert list(conn.iterdump())==before
app.button(key=f'project_member_open_{p}').click().run()
field(app,'selectbox','Virksomhed').select(b)
field(app,'button','Annuller').click().run()
assert list(conn.iterdump())==before
app.button(key=f'project_edit_member_{p}_{a}').click().run()
field(app,'multiselect','Projektroller').set_value(['Betaler'])
field(app,'button','Annuller').click().run()
assert list(conn.iterdump())==before
app.button(key=f'project_open_track_{track}').click().run()
assert app.button(key='business_return_project').label=='Tilbage til projekt: TEST Handlinger'
from services.project_service import remove_relation
remove_relation('track',p,track)
app.run()
assert not any(x.key=='business_return_project' for x in app.button)
assert not len(app.exception),list(app.exception)
assert conn.execute('SELECT title FROM commercial_tracks WHERE id=?',(track,)).fetchone()[0]=='TEST Eksisterende behov'
conn.close()
''')
