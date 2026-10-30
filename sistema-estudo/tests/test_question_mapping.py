import contextlib
import gc
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
import roadmap
import map_questions
import question_links
from question_mapping_rules import normalize


class MappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db,cls.original_port=server.STUDY_DB,server.PORT
        cls.source_hash=hashlib.sha256(map_questions.CONTENT.read_bytes()).hexdigest()
        cls.questions,cls.links,cls.report=map_questions.build()
        cls.by_id={q['ocorrencia_id']:q for q in cls.questions}
        cls.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        server.STUDY_DB=Path(cls.temp.name)/'study.sqlite'
        server.init_db()
        with contextlib.redirect_stdout(io.StringIO()):
            roadmap.install(server.STUDY_DB)
        with server.study_db() as con:
            con.execute("INSERT INTO subjects VALUES('manual-subject','Pessoal','before')")
            con.execute("INSERT INTO topics VALUES('manual-topic','manual-subject','Tópico',0,'before')")
            con.execute("INSERT INTO lessons(lesson_id,topic_id,title,completed_at,created_at) VALUES('manual-lesson','manual-topic','Aula','before','before')")
            con.execute('INSERT INTO lesson_questions VALUES(?,?,0)',('manual-lesson',cls.questions[0]['ocorrencia_id']))
        cls.result=map_questions.apply_links(cls.links,cls.report,server.STUDY_DB)
        cls.http=server.StudyServer(('127.0.0.1',0),server.Handler)
        server.PORT=cls.http.server_address[1]
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()
        cls.url='http://127.0.0.1:'+str(server.PORT)

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join()
        server.STUDY_DB,server.PORT=cls.original_db,cls.original_port
        assert hashlib.sha256(map_questions.CONTENT.read_bytes()).hexdigest()==cls.source_hash
        gc.collect();cls.temp.cleanup()

    def request(self,path,method='GET',body=None):
        req=Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,method=method,
                    headers={'Origin':self.url,'Content-Type':'application/json'})
        with urlopen(req,timeout=15) as response:return json.load(response)

    def test_every_occurrence_audited_and_evidence_localizable(self):
        audit=[json.loads(line) for line in (map_questions.OUTPUT/'auditoria-toda-base.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len(audit),len(self.questions))
        self.assertEqual(len({q['ocorrencia_id'] for q in self.questions}),len(audit))
        self.assertEqual(self.report['linked_occurrences']+self.report['unlinked_occurrences'],len(audit))
        self.assertEqual(len({(l['lesson_id'],l['occurrence_id']) for l in self.links}),len(self.links))
        self.assertEqual(set(self.report['by_bank']),{'FCC','FGV','ESAF','Cebraspe','Vunesp','Fundatec'})
        for link in self.links:
            q=self.by_id[link['occurrence_id']]
            self.assertTrue(link['syllabus_excerpt'])
            for evidence in link['evidence']:
                raw=q['enunciado_original'] if evidence['field']=='enunciado_original' else ' '.join(a['texto_original'] for a in q['alternatives'])
                self.assertIn(normalize(evidence['text']),normalize(raw))

    def test_regressions_for_incidental_terms_and_foreign_text(self):
        def keys(occurrence):return {l['lesson_id'].removeprefix('apofp26_') for l in self.links if l['occurrence_id']==occurrence}
        self.assertEqual(keys('o_60e4d767a7a99ef8d561751d'),{'dad_01'})
        self.assertEqual(keys('o_8a182db1d09d77dac2b91d35'),{'da_02'})
        self.assertEqual(keys('o_5f233977124cf8019589e613'),{'por_02'})
        self.assertNotIn('a01_05',keys('o_de9670a96ee7b4912d011acf'))
        self.assertEqual(keys('o_57e52d63879dd3b3c0877dde'),set())
        for q in self.questions:
            if 'The three main arguments against big data' in q['enunciado_original']:
                self.assertEqual(keys(q['ocorrencia_id']),set())
        self.assertEqual(keys('o_a56573a4560c21973205d78c'),{'con_02'})
        # The financial case text is not a Portuguese reading-comprehension item.
        for q in self.questions:
            if q['concurso']=='2025-SEFAZ-RJ-FINANCAS':
                self.assertFalse(any(key.startswith('por_') for key in keys(q['ocorrencia_id'])),q['enunciado_original'])

    def test_import_idempotent_atomic_and_existing_data_preserved(self):
        again=map_questions.apply_links(self.links,self.report,server.STUDY_DB)
        self.assertEqual(again['added'],0)
        with server.study_db() as con:
            original=self.links[0]
            con.execute('INSERT INTO lesson_questions VALUES(?,?,0)',('apofp26_mat_08',original['occurrence_id']))
            con.execute('''INSERT INTO lesson_question_mappings SELECT 'apofp26_mat_08',occurrence_id,relation,confidence,method,score,evidence_json,syllabus_excerpt,note,run_id
                           FROM lesson_question_mappings WHERE lesson_id=? AND occurrence_id=?''',(original['lesson_id'],original['occurrence_id']))
        synced=map_questions.apply_links(self.links,self.report,server.STUDY_DB)
        self.assertEqual(synced['removed_obsolete_generated'],1)
        with server.study_db() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM lesson_questions').fetchone()[0],len(self.links)+1)
            self.assertEqual(con.execute("SELECT completed_at FROM lessons WHERE lesson_id='manual-lesson'").fetchone()[0],'before')
            before=con.execute('SELECT count(*) FROM question_mapping_runs').fetchone()[0]
        broken=[dict(self.links[0]),dict(self.links[1],lesson_id='nonexistent-lesson')]
        with self.assertRaises(sqlite3.IntegrityError):map_questions.apply_links(broken,self.report,server.STUDY_DB)
        with server.study_db() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM question_mapping_runs').fetchone()[0],before)
            self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_large_lesson_api_preserves_provenance_and_hides_answers(self):
        lesson=self.request('/api/lessons/apofp26_por_02')
        ids=lesson['occurrence_ids']
        self.assertGreater(len(ids),100)
        self.assertEqual(len(ids),len(lesson['questions']))
        for q in lesson['questions']:
            self.assertTrue(q['mapping']['evidence'])
            self.assertNotIn('reference_answer',q)
            self.assertNotIn('resposta_referencia',q)
            self.assertNotIn('answer',q['mapping'])
        saved=self.request('/api/lessons/apofp26_por_02/questions','PUT',dict(occurrence_ids=list(reversed(ids))))
        self.assertEqual(saved['occurrence_ids'],list(reversed(ids)))
        self.assertTrue(all(q['mapping'] for q in saved['questions']))
        self.request('/api/lessons/apofp26_por_02/questions','PUT',dict(occurrence_ids=ids))

    def test_session_selection_avoids_duplicate_content_and_rotates(self):
        with server.study_db() as study,server.content_db() as content:
            first=question_links.session_pool(study,content,'apofp26_por_02')
            self.assertEqual(len(first['questionPool']),12)
            items=question_links.content_items(content,first['questionPool'])
            self.assertEqual(len({q['questao_id'] for q in items}),12)
            self.assertNotIn(first['pretestOccurrenceId'],first['practiceOccurrenceIds'])
            self.assertNotIn(first['recallOccurrenceId'],first['practiceOccurrenceIds'])
        q=server.content_question(first['pretestOccurrenceId'],include_answer=True)
        answer=q['resposta_referencia']
        outcome=server.answer_snapshot(first['pretestOccurrenceId'],answer,'free')
        self.assertTrue(outcome['correct'])
        with server.study_db() as study,server.content_db() as content:
            second=question_links.session_pool(study,content,'apofp26_por_02')
            self.assertNotEqual(first['pretestOccurrenceId'],second['pretestOccurrenceId'])
            self.assertNotIn(first['pretestOccurrenceId'],second['questionPool'])
        session=self.request('/api/lessons/apofp26_por_02/sessions','POST',{})
        self.assertEqual(len(session['payload']['questionPool']),12)
        resumed=self.request('/api/lessons/apofp26_por_02/sessions','POST',{})
        self.assertEqual(resumed['payload']['questionPool'],session['payload']['questionPool'])
        boot=self.request('/api/bootstrap')
        mapping=boot['roadmap']['question_mapping']
        self.assertEqual(mapping['total_occurrences'],len(self.questions))
        self.assertEqual(mapping['current_links'],len(self.links))
        self.assertEqual(mapping['current_lessons_with_questions'],self.report['lessons_with_questions'])


if __name__=='__main__':unittest.main(verbosity=2)
