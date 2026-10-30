"""Safety checks for the read-only history-cleanup tools."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from history_cleanup_common import reject_path_inside_git_repository  # noqa: E402
from history_cleanup_mailmap import create_mailmap, raw_identity_pairs  # noqa: E402
from history_cleanup_plan import classify_path, create_plan  # noqa: E402
from history_cleanup_validate import validate  # noqa: E402


def git(repository: Path, *arguments: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    return result.stdout.strip()


def init_repository(path: Path) -> Path:
    path.mkdir()
    git(path, "init", "-b", "main")
    git(path, "config", "user.name", "Test Committer")
    git(path, "config", "user.email", "committer@example.invalid")
    return path


class HistoryCleanupTests(unittest.TestCase):
    def test_private_artifacts_cannot_be_written_inside_a_checkout(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = init_repository(Path(temporary) / "source")
            with self.assertRaisesRegex(ValueError, "checkout Git"):
                reject_path_inside_git_repository(ROOT / "private-plan.json", repository, "O plano")

    def test_path_classifier_is_conservative_around_code_and_fixtures(self):
        for path in (
            "base-questoes/dados/conteudo.sqlite",
            "base-questoes/dados/fontes-visuais/page-01.png",
            "sistema-estudo/dados/questions.jsonl",
            "runs/piloto-01/evidencias/foto.webp",
            "packages/app/src/questions.jsonl",
        ):
            with self.subTest(path=path):
                self.assertEqual(classify_path(path)[0], "remove")

        for path in (
            "base-questoes/dados/importer.py",
            "biblioteca-concursos/README.md",
            "packages/app/tests/fixtures/golden.json",
            "docs/example.png",
            "docs/manual.pdf",
        ):
            with self.subTest(path=path):
                self.assertEqual(classify_path(path)[0], "review")

        self.assertEqual(classify_path("packages/app/src/app.py")[0], "keep")

    def test_plan_records_refs_tree_digest_and_explicit_review_decisions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = init_repository(root / "source")
            files = {
                "base-questoes/dados/questions.jsonl": "private fixture\n",
                "base-questoes/dados/importer.py": "print('review')\n",
                "packages/app/src/app.py": "print('keep')\n",
                "packages/app/tests/fixtures/golden.json": "{}\n",
                "docs/example.png": "image bytes\n",
            }
            for relative, contents in files.items():
                path = repository / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents, encoding="utf-8")
            git(repository, "add", ".")
            git(repository, "commit", "-m", "Add synthetic history")

            initial = create_plan(repository, "refs/heads/main", None)
            self.assertEqual(len(initial["refs_before"]), 1)
            self.assertIn("base-questoes/dados/questions.jsonl", initial["remove_paths"])
            self.assertEqual(len(initial["unresolved_review_paths"]), 3)
            self.assertEqual(initial["history_path_counts"]["keep"], 1)
            self.assertEqual(initial["current_tree_before"]["preserved_files"], 4)

            decisions_path = root / "decisions.json"
            decisions_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "decisions": [
                            {
                                "path": "base-questoes/dados/importer.py",
                                "decision": "keep",
                                "reason": "Synthetic source file retained for the test.",
                            },
                            {
                                "path": "packages/app/tests/fixtures/golden.json",
                                "decision": "keep",
                                "reason": "Synthetic redistributable test fixture.",
                            },
                            {
                                "path": "docs/example.png",
                                "decision": "keep",
                                "reason": "Synthetic public documentation asset.",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            decisions_path.chmod(0o600)
            reviewed = create_plan(repository, "refs/heads/main", decisions_path)
            self.assertEqual(reviewed["unresolved_review_paths"], [])
            self.assertEqual(
                reviewed["reviewed_keep_paths"],
                [
                    "base-questoes/dados/importer.py",
                    "docs/example.png",
                    "packages/app/tests/fixtures/golden.json",
                ],
            )
            self.assertEqual(reviewed["history_path_counts"]["keep"], 1)
            self.assertEqual(reviewed["current_tree_before"]["preserved_files"], 4)

            mailmap = root / "mailmap.txt"
            mailmap.write_text(
                "Canonical Owner <123+owner@users.noreply.github.com> Test Committer <committer@example.invalid>\n",
                encoding="utf-8",
            )
            mailmap.chmod(0o600)
            cleaned = init_repository(root / "cleaned")
            git(cleaned, "config", "user.name", "Canonical Owner")
            git(cleaned, "config", "user.email", "123+owner@users.noreply.github.com")
            for relative in (
                "base-questoes/dados/importer.py",
                "packages/app/src/app.py",
                "packages/app/tests/fixtures/golden.json",
                "docs/example.png",
            ):
                source = repository / relative
                destination = cleaned / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
            git(cleaned, "add", ".")
            git(cleaned, "commit", "-m", "Synthetic rewritten history")

            report = validate(cleaned, reviewed, mailmap)
            self.assertTrue(report["passed"], report["checks"])
            self.assertEqual(report["refs"][0]["status"], "rewritten")
            self.assertEqual(report["paths"]["remaining_remove_count"], 0)
            self.assertTrue(report["mailmap"]["canonical_identity_present"])
            self.assertEqual(report["mailmap"]["source_identities_remaining"], 0)
            self.assertTrue(report["current_tree"]["preserved_digest_matches"])

    def test_mailmap_maps_only_explicit_owner_pairs_across_multiple_commits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = init_repository(root / "source")
            first_env = os.environ.copy()
            first_env.update(
                {
                    "GIT_AUTHOR_NAME": "Owner Alias",
                    "GIT_AUTHOR_EMAIL": "owner-old@example.invalid",
                }
            )
            git(repository, "commit", "--allow-empty", "-m", "first", env=first_env)

            second_env = os.environ.copy()
            second_env.update(
                {
                    "GIT_AUTHOR_NAME": "Guest Contributor",
                    "GIT_AUTHOR_EMAIL": "guest@example.invalid",
                    "GIT_COMMITTER_NAME": "Owner Alias",
                    "GIT_COMMITTER_EMAIL": "owner-old@example.invalid",
                }
            )
            git(repository, "commit", "--allow-empty", "-m", "second", env=second_env)

            tag_env = os.environ.copy()
            tag_env.update(
                {
                    "GIT_COMMITTER_NAME": "Owner Tagger",
                    "GIT_COMMITTER_EMAIL": "owner-tagger@example.invalid",
                }
            )
            git(repository, "tag", "-a", "v-test", "-m", "synthetic tag", env=tag_env)

            pairs = raw_identity_pairs(repository)
            owner_pair = ("Owner Alias", "owner-old@example.invalid")
            self.assertIn(owner_pair, pairs)
            tagger_pair = ("Owner Tagger", "owner-tagger@example.invalid")
            self.assertIn(tagger_pair, pairs)
            self.assertIn(("Guest Contributor", "guest@example.invalid"), pairs)
            self.assertIn(("Test Committer", "committer@example.invalid"), pairs)

            identities = root / "owner-identities.json"
            identities.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "identities": [
                            {"name": owner_pair[0], "email": owner_pair[1]},
                            {"name": tagger_pair[0], "email": tagger_pair[1]},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            identities.chmod(0o600)
            mailmap = root / "mailmap.txt"
            self.assertEqual(
                create_mailmap(
                    repository,
                    identities,
                    mailmap,
                    "Owner Canonical",
                    "123+owner@users.noreply.github.com",
                ),
                2,
            )
            if os.name == "posix":
                self.assertEqual(mailmap.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                git(
                    repository,
                    "-c",
                    f"mailmap.file={mailmap}",
                    "check-mailmap",
                    "Owner Alias <owner-old@example.invalid>",
                ),
                "Owner Canonical <123+owner@users.noreply.github.com>",
            )
            self.assertEqual(
                git(
                    repository,
                    "-c",
                    f"mailmap.file={mailmap}",
                    "check-mailmap",
                    "Owner Tagger <owner-tagger@example.invalid>",
                ),
                "Owner Canonical <123+owner@users.noreply.github.com>",
            )
            self.assertEqual(
                git(
                    repository,
                    "-c",
                    f"mailmap.file={mailmap}",
                    "check-mailmap",
                    "Guest Contributor <guest@example.invalid>",
                ),
                "Guest Contributor <guest@example.invalid>",
            )


if __name__ == "__main__":
    unittest.main()
