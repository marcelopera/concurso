import contextlib
import gc
import io
import json
import sqlite3
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import roadmap
import server


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db = server.STUDY_DB
        cls.original_port = server.PORT
        cls.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        server.STUDY_DB = Path(cls.temp.name)/'study.sqlite'
        server.init_db()
        with server.study_db() as con:
            con.execute("INSERT INTO subjects VALUES('personal','Pessoal','old')")
            con.execute("INSERT INTO topics VALUES('personal-topic','personal','Tópico',0,'old')")
            con.execute("INSERT INTO lessons(lesson_id,topic_id,title,completed_at,created_at) VALUES('personal-lesson','personal-topic','Minha aula','finished','old')")
        with contextlib.redirect_stdout(io.StringIO()):
            roadmap.install(server.STUDY_DB)
        cls.plan = json.loads(roadmap.PLAN_FILE.read_text(encoding='utf-8'))
        cls.http = server.StudyServer(('127.0.0.1',0),server.Handler)
        server.PORT = cls.http.server_address[1]
        cls.thread = threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:'+str(cls.http.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()
        server.STUDY_DB = cls.original_db
        server.PORT = cls.original_port
        gc.collect()
        cls.temp.cleanup()

    def request(self,path,method='GET',body=None):
        request=Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,
                        method=method,headers={'Content-Type':'application/json','Origin':self.url})
        with urlopen(request) as response:
            return json.load(response)

    def test_all_syllabus_text_partitioned(self):
        self.assertEqual(len(self.plan['subjects']),11)
        for subject in self.plan['subjects']:
            units=sorted(subject['lessons'],key=lambda u:u['source_offset'])
            self.assertEqual(' '.join(u['source_excerpt'] for u in units),subject['source_text'])
            self.assertTrue(all(u['checklist'] and u['pages'] for u in units))
        self.assertEqual(sum(s['points'] for s in self.plan['subjects'] if s['exam']=='P1'),112)
        self.assertEqual(sum(s['questions'] for s in self.plan['subjects'] if s['exam']=='P1'),80)

    def test_invalid_catalog_page_returns_400(self):
        with self.assertRaises(HTTPError) as error:
            self.request('/api/catalog?page=abc')
        self.assertEqual(error.exception.code, 400)

    def test_legacy_progress_upgrade_preserves_data_and_rejects_future_versions(self):
        with server.study_db() as con:
            con.execute("UPDATE lessons SET completed_at='preservado' WHERE lesson_id='personal-lesson'")
            con.execute('PRAGMA user_version = 0')
        server.init_db()
        server.init_db()
        with server.study_db() as con:
            self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertEqual(con.execute('SELECT count(*) FROM schema_migrations WHERE version=1').fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT completed_at FROM lessons WHERE lesson_id='personal-lesson'").fetchone()[0], 'preservado')
            con.execute('PRAGMA user_version = 2')
        with self.assertRaises(RuntimeError):
            server.init_db()
        with server.study_db() as con:
            con.execute('PRAGMA user_version = 1')

    def test_library_resolves_legacy_paths_and_rejects_escape(self):
        original = server.LIBRARY_ROOT
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            try:
                server.LIBRARY_ROOT = Path(tmp).resolve()
                pdf = server.LIBRARY_ROOT / 'banca' / 'prova.pdf'
                pdf.parent.mkdir()
                pdf.write_bytes(b'%PDF-test')
                self.assertEqual(server.safe_library_file('banca/prova.pdf'), pdf)
                self.assertEqual(server.safe_library_file(r'C:\old\biblioteca-concursos\banca\prova.pdf'), pdf)
                self.assertIsNone(server.safe_library_file('../prova.pdf'))
                self.assertIsNone(server.safe_library_file(r'C:\outside\prova.pdf'))
            finally:
                server.LIBRARY_ROOT = original

    def test_pdf_streaming_and_ranges(self):
        original_root, original_content = server.LIBRARY_ROOT, server.CONTENT_DB
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            try:
                server.LIBRARY_ROOT = Path(tmp).resolve()
                server.CONTENT_DB = server.LIBRARY_ROOT / 'catalog.sqlite'
                (server.LIBRARY_ROOT / 'prova.pdf').write_bytes(b'0123456789')
                with sqlite3.connect(server.CONTENT_DB) as con:
                    con.execute('CREATE TABLE documentos(documento_id TEXT, arquivo_local TEXT, nome TEXT)')
                    con.execute('INSERT INTO documentos VALUES(?,?,?)', ('d', 'prova.pdf', 'prova.pdf'))
                con.close()
                def get(value=None):
                    headers = {'Origin': self.url}
                    if value is not None:
                        headers['Range'] = value
                    return urlopen(Request(self.url + '/api/library/file?document_id=d', headers=headers))
                with get() as response:
                    self.assertEqual(response.read(), b'0123456789')
                    self.assertEqual(response.headers['Accept-Ranges'], 'bytes')
                with get('bytes=2-5') as response:
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.headers['Content-Range'], 'bytes 2-5/10')
                    self.assertEqual(response.read(), b'2345')
                with get('bytes=-3') as response:
                    self.assertEqual(response.read(), b'789')
                for value in ('bytes=100-', 'bytes=-0', 'bytes=1-2,4-5'):
                    with self.assertRaises(HTTPError) as error:
                        get(value)
                    self.assertEqual(error.exception.code, 416)
                    self.assertEqual(error.exception.headers['Content-Range'], 'bytes */10')
                    error.exception.close()
            finally:
                server.LIBRARY_ROOT, server.CONTENT_DB = original_root, original_content

    def test_calendar_covers_each_unit_once_and_four_hours_daily(self):
        units={u['lesson_id']:u for s in self.plan['subjects'] for u in s['lessons']}
        scheduled=[]
        for day in self.plan['days']:
            scheduled.extend(day['lessons'])
            self.assertEqual(sum(units[lid]['minutes'] for lid in day['lessons'])+sum(a['minutes'] for a in day['activities']),240)
            self.assertTrue(all(units[lid]['scheduled_date']==day['date'] for lid in day['lessons']))
            self.assertTrue(all(day['date']<=self.plan['coverage_deadline'] for _ in day['lessons']))
            expected={lid for lid,u in units.items() if (date.fromisoformat(day['date'])-date.fromisoformat(u['scheduled_date'])).days in [1,7,21]}
            self.assertEqual(set(day['review_lesson_ids']),expected)
        self.assertEqual(Counter(scheduled),Counter(units.keys()))
        self.assertEqual(len(self.plan['days']),52)
        self.assertEqual(len([a for d in self.plan['days'] for a in d['activities'] if a['kind']=='simulation']),4)

    def test_import_is_idempotent_and_preserves_history(self):
        with server.study_db() as con:
            con.execute("UPDATE lessons SET completed_at='kept' WHERE lesson_id='apofp26_afo_01'")
        with contextlib.redirect_stdout(io.StringIO()):
            roadmap.install(server.STUDY_DB)
        with server.study_db() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM lessons').fetchone()[0],95)
            self.assertEqual(con.execute("SELECT completed_at FROM lessons WHERE lesson_id='personal-lesson'").fetchone()[0],'finished')
            self.assertEqual(con.execute("SELECT completed_at FROM lessons WHERE lesson_id='apofp26_afo_01'").fetchone()[0],'kept')
            self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(),[])
            con.execute("UPDATE lessons SET completed_at=NULL WHERE lesson_id='apofp26_afo_01'")

    def test_lesson_api_and_persistent_activity_progress(self):
        lesson=self.request('/api/lessons/apofp26_a01_01')
        self.assertIn('superávit financeiro',lesson['roadmap']['source_excerpt'])
        self.assertEqual(lesson['roadmap']['exam'],'P2')
        before=self.request('/api/bootstrap')['roadmap']['stats']['completed']
        aid='review-2026-10-29'
        response=self.request('/api/roadmap/activities/'+aid,'PUT',{'completed':True,'note':'revisto'})
        self.assertTrue(response['completed_at'])
        plan=self.request('/api/bootstrap')['roadmap']
        self.assertEqual(plan['days'][0]['activities'][0]['note'],'revisto')
        self.assertTrue(plan['days'][0]['activities'][0]['completed_at'])
        self.assertEqual(plan['stats']['completed'],before)
        self.request('/api/roadmap/activities/'+aid,'PUT',{'completed':False})
        self.assertIsNone(self.request('/api/bootstrap')['roadmap']['days'][0]['activities'][0]['completed_at'])
        for activity,body in [('unknown',{'completed':True}),(aid,{'completed':'yes'})]:
            with self.assertRaises(HTTPError) as caught:
                self.request('/api/roadmap/activities/'+activity,'PUT',body)
            self.assertEqual(caught.exception.code,400)
            caught.exception.close()


if __name__=='__main__':
    unittest.main(verbosity=2)
