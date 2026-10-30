"""Keep package dependencies and the HTTP/persistence boundary explicit."""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "packages/estudo/backend/src/estudo"
PIPELINE = ROOT / "packages/pipeline/src/concurso_pipeline"
CONTRACTS = ROOT / "packages/contracts/src/concurso_contracts"


def imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


class ArchitectureTests(unittest.TestCase):
    def test_packages_only_depend_on_the_shared_contract(self):
        for folder, forbidden in (
            (BACKEND, {"concurso_pipeline", "server", "roadmap", "profiles", "question_links", "catalogo"}),
            (PIPELINE, {"estudo", "catalogo"}),
            (CONTRACTS, {"estudo", "concurso_pipeline"}),
        ):
            for path in folder.rglob("*.py"):
                with self.subTest(path=path.relative_to(ROOT)):
                    dependencies = {name.split(".")[0] for name in imports(ast.parse(path.read_text(encoding="utf-8")))}
                    self.assertFalse(dependencies & forbidden, dependencies & forbidden)

    def test_http_and_services_do_not_execute_sql(self):
        for folder in (BACKEND / "api", BACKEND / "services"):
            for path in folder.glob("*.py"):
                with self.subTest(path=path.relative_to(ROOT)):
                    tree = ast.parse(path.read_text(encoding="utf-8"))
                    calls = [
                        node.func.attr
                        for node in ast.walk(tree)
                        if isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr in {"execute", "executemany", "executescript"}
                    ]
                    self.assertEqual(calls, [])

    def test_repositories_do_not_import_services_or_http(self):
        for path in (BACKEND / "repositories").glob("*.py"):
            with self.subTest(path=path.name):
                for name in imports(ast.parse(path.read_text(encoding="utf-8"))):
                    self.assertFalse(name.startswith(("estudo.services", "estudo.api", "estudo.app")), name)
