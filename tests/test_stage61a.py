import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

BOOTSTRAP='''
from streamlit.testing.v1 import AppTest
from tests.stage61_fixture import populate
from services.project_service import save_project,save_participant,save_workstream,link_track
from db import connect
from views.projects import stream_label
a,b,track=populate()
conn=connect()
def start(p=None):
    app=AppTest.from_file('app.py')
    app.session_state['page']='Forretning'
    app.session_state['business_view']='Projekter'
    if p: app.session_state['project_selected']=p
    return app.run(timeout=30)
def field(app,kind,label):
    return next(x for x in getattr(app,kind) if x.label==label)
def submit(app,label):
    next(x for x in app.button if x.label==label and str(x.key).startswith('FormSubmitter:')).click().run()
    assert not len(app.exception),list(app.exception)
def receipt(app,text):
    assert any(text in x.value for x in app.success),list(app.success)
def readonly(app):
    assert not len(app.text_input) and not len(app.text_area) and not len(app.multiselect)
'''


class Stage61aTests(unittest.TestCase):
    def run_ui(self,script):
        parent=ROOT/'.test-tmp'
        parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent,prefix='stage61a-') as directory:
            root=Path(directory)
            runtime=root/'runtime'
            runtime.mkdir()
            env=os.environ.copy()
            env.update(FRANK_MONITOR_MODE='test',FRANK_MONITOR_DATA_DIR=str(root/'data'),
                       FRANK_MONITOR_PRODUCTION_DATA_DIR=str(root/'production'),TEMP=str(runtime),TMP=str(runtime))
            result=subprocess.run([sys.executable,'-c',BOOTSTRAP+script],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_create_reset_explicit_choices_receipts_links_and_return(self):
        self.run_ui('''
app=start()
readonly(app)
app.button(key='project_create_open').click().run()
field(app,'text_input','Projekttitel').set_value('TEST Ny start')
field(app,'text_area','Formål').set_value('TEST Formål')
submit(app,'Opret projekt')
p=app.session_state['project_selected']
receipt(app,'Projektet er oprettet.')
readonly(app)
app.button(key='project_create_open').click().run()
assert field(app,'text_input','Projekttitel').value==''
assert field(app,'text_area','Formål').value==''
assert field(app,'selectbox','Projektstatus').value=='Planlagt'
field(app,'button','Annuller').click().run()
app.button(key=f'project_member_open_{p}').click().run()
assert field(app,'selectbox','Virksomhed').value is None
assert field(app,'multiselect','Projektroller').value==[]
submit(app,'Gem deltager')
assert len(app.error) and conn.execute('SELECT COUNT(*) FROM project_companies').fetchone()[0]==0
field(app,'selectbox','Virksomhed').select(a)
field(app,'multiselect','Projektroller').set_value(['Koordinator','Betaler'])
submit(app,'Gem deltager')
receipt(app,'Deltageren er tilknyttet')
readonly(app)
app.button(key=f'project_member_open_{p}').click().run()
assert field(app,'selectbox','Virksomhed').value is None
assert field(app,'multiselect','Projektroller').value==[]
field(app,'button','Annuller').click().run()
app.button(key=f'project_stream_open_{p}').click().run()
field(app,'text_input','Sportitel').set_value('TEST Spor')
field(app,'selectbox','Virksomhed / fælles').select(a)
field(app,'selectbox','Sporstatus').select('I gang')
submit(app,'Gem arbejdsspor')
receipt(app,'Arbejdssporet er oprettet.')
readonly(app)
app.button(key=f'project_stream_open_{p}').click().run()
assert field(app,'text_input','Sportitel').value==''
assert field(app,'selectbox','Virksomhed / fælles').value is None
assert field(app,'selectbox','Sporstatus').value=='Planlagt'
field(app,'button','Annuller').click().run()
app.button(key=f'project_link_open_{p}').click().run()
assert field(app,'selectbox','Eksisterende forløb').value is None
submit(app,'Tilknyt forløb')
assert len(app.error) and conn.execute('SELECT COUNT(*) FROM project_tracks').fetchone()[0]==0
before=[tuple(r) for r in conn.execute('SELECT * FROM commercial_tracks')]
field(app,'selectbox','Eksisterende forløb').select(track)
submit(app,'Tilknyt forløb')
receipt(app,'Forretningsforløbet er tilknyttet')
readonly(app)
app.button(key=f'project_open_track_{track}').click().run()
assert not len(app.exception),list(app.exception)
assert app.radio(key='business_view').value=='Forløb'
assert app.button(key='business_return_project').label=='Tilbage til projekt: TEST Ny start'
app.button(key='business_return_project').click().run()
assert not len(app.exception),list(app.exception)
assert app.radio(key='business_view').value=='Projekter'
assert app.session_state['project_selected']==p
app.button(key=f'project_unlink_track_{track}').click().run()
receipt(app,'Selve forretningsforløbet er ikke slettet.')
assert [tuple(r) for r in conn.execute('SELECT * FROM commercial_tracks')]==before
assert conn.execute('SELECT COUNT(*) FROM project_tracks').fetchone()[0]==0
app.button(key=f'project_link_open_{p}').click().run()
assert field(app,'selectbox','Eksisterende forløb').value is None
assert not conn.execute('PRAGMA foreign_key_check').fetchall()
conn.close()
''')

    def test_read_only_edit_duplicate_titles_project_switch_and_empty_guidance(self):
        self.run_ui('''
p=save_project('TEST Oversigt')
other=save_project('TEST Uden deltagere')
save_participant(p,a,['Koordinator','Betaler'])
save_participant(p,b,['Deltager'])
s1=save_workstream(p,'TEST Samme titel')
s2=save_workstream(p,'TEST Samme titel',a)
s3=save_workstream(p,'TEST Samme titel',a)
labels=[stream_label(dict(r)) for r in conn.execute('SELECT w.*,c.name AS company FROM project_workstreams w LEFT JOIN companies c ON c.id=w.company_id')]
assert len(set(labels))==3
assert 'Fælles spor' in labels[0] and 'TEST Alfa' in labels[1]
app=start(p)
readonly(app)
assert all(any(label==x.value for x in app.markdown) for label in labels)
before=list(conn.iterdump())
app.run()
assert list(conn.iterdump())==before
app.button(key=f'project_edit_stream_{s2}').click().run()
assert field(app,'text_input','Sportitel').value=='TEST Samme titel'
assert field(app,'selectbox','Virksomhed / fælles').value==a
field(app,'text_input','Sportitel').set_value('TEST Rettet spor')
submit(app,'Gem arbejdsspor')
receipt(app,'Arbejdssporet er opdateret.')
readonly(app)
assert conn.execute('SELECT title FROM project_workstreams WHERE id=?',(s2,)).fetchone()[0]=='TEST Rettet spor'
assert conn.execute('SELECT title FROM project_workstreams WHERE id=?',(s3,)).fetchone()[0]=='TEST Samme titel'
app.button(key=f'project_edit_member_{p}_{a}').click().run()
assert set(field(app,'multiselect','Projektroller').value)=={'Koordinator','Betaler'}
field(app,'multiselect','Projektroller').set_value(['Deltager'])
submit(app,'Gem deltager')
receipt(app,'Deltageren er opdateret.')
readonly(app)
app.button(key=f'project_edit_open_{p}').click().run()
field(app,'text_input','Projekttitel').set_value('TEST Redigeret projekt')
submit(app,'Gem projekt')
receipt(app,'Projektet er opdateret.')
readonly(app)
app.button(key=f'project_edit_stream_{s1}').click().run()
app.selectbox(key='project_selected').select(other).run()
assert not len(app.exception),list(app.exception)
readonly(app)
app.button(key=f'project_link_open_{other}').click().run()
assert any('Ingen forretningsforløb kan tilknyttes endnu.' in x.value for x in app.info)
assert not any(x.label=='Eksisterende forløb' for x in app.selectbox)
assert not conn.execute('PRAGMA foreign_key_check').fetchall()
conn.close()
''')
