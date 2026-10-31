"""Concurrent server instances must retain their own storage and configuration."""

import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, closing
from dataclasses import replace
from pathlib import Path
from urllib.request import urlopen

from concurso_contracts.catalog.criar_demo import criar
from estudo.app import Application
from estudo.config import Settings
from estudo.initialization import initialize_once, prepare_study


class ApplicationIsolationTests(unittest.TestCase):
    def test_initialization_requires_an_external_plan_and_preserves_existing_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = Application(replace(Settings.from_env(), study_db=root / "study.sqlite", plan_file=None))
            with self.assertRaisesRegex(ValueError, "arquivo do plano"):
                prepare_study(app)
            self.assertFalse(app.settings.study_db.exists())
            with self.assertRaises(FileNotFoundError):
                prepare_study(app, root / "missing.json")
            self.assertFalse(app.settings.study_db.exists())
            app.init_db()
            before = app.settings.study_db.read_bytes()
            self.assertFalse(initialize_once(app, root / "missing.json"))
            self.assertEqual(app.settings.study_db.read_bytes(), before)

    def test_two_running_applications_keep_their_catalog_and_progress(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root = Path(tmp)
            apps, urls = [], []
            for index in range(2):
                folder = root / str(index)
                folder.mkdir()
                settings = replace(
                    Settings.from_env(),
                    study_db=folder / "study.sqlite",
                    content_db=folder / "content.sqlite",
                )
                criar(settings.content_db)
                with closing(sqlite3.connect(settings.content_db)) as con, con:
                    con.execute("UPDATE questoes SET enunciado_original=?", (f"Catálogo {index}",))
                app = Application(settings)
                app.initialize()
                server = app.http_server(("127.0.0.1", 0))
                server.quiet = True
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                stack.callback(thread.join)
                stack.callback(server.server_close)
                stack.callback(server.shutdown)
                apps.append(app)
                urls.append(f"http://127.0.0.1:{server.server_port}")

            def catalog(index):
                with urlopen(urls[index] + "/api/catalog") as response:
                    return json.load(response)["items"][0]["stem"]

            with ThreadPoolExecutor(max_workers=4) as pool:
                requests = list(pool.map(catalog, [0, 1] * 6))
            self.assertEqual(requests, ["Catálogo 0", "Catálogo 1"] * 6)
            with apps[0].study_db() as con:
                con.execute("INSERT INTO subjects VALUES('one', 'Só no primeiro', 'now')")
            self.assertEqual(apps[0].bootstrap()["subjects"][0]["name"], "Só no primeiro")
            self.assertEqual(apps[1].bootstrap()["subjects"], [])
