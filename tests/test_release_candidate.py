"""Regression checks for the read-only release candidate gate."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.check_release_candidate import check_required_statuses, matching_paths


def git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class ReleaseCandidateTests(unittest.TestCase):
    def test_history_scan_matches_unicode_private_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            git(repository, "init", "--quiet", "--initial-branch=main")
            private_file = repository / "base-questoes" / "dados" / "questões.sqlite"
            private_file.parent.mkdir(parents=True)
            private_file.write_bytes(b"synthetic")
            git(repository, "add", ".")
            git(
                repository,
                "-c",
                "user.name=Release Gate Test",
                "-c",
                "user.email=release-gate@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "fixture",
            )

            self.assertEqual(matching_paths(git(repository, "rev-parse", "HEAD"), repository), 1)

    def test_successful_check_run_from_required_app_passes(self):
        with patch(
            "tools.check_release_candidate.github_json",
            side_effect=[
                {"required_status_checks": {"checks": [{"context": "CodeQL", "app_id": 42}]}},
                {
                    "check_runs": [
                        {
                            "id": 9,
                            "name": "CodeQL",
                            "app": {"id": 42},
                            "status": "completed",
                            "conclusion": "success",
                        }
                    ]
                },
                [],
            ],
        ):
            self.assertEqual(check_required_statuses("owner/repo", "a" * 40), [])

    def test_commit_status_cannot_satisfy_check_bound_to_another_app(self):
        with patch(
            "tools.check_release_candidate.github_json",
            side_effect=[
                {"required_status_checks": {"checks": [{"context": "CodeQL", "app_id": 42}]}},
                {
                    "check_runs": [
                        {"id": 9, "name": "CodeQL", "app": {"id": 7}, "status": "completed", "conclusion": "success"}
                    ]
                },
                [{"context": "CodeQL", "state": "success"}],
            ],
        ):
            self.assertEqual(check_required_statuses("owner/repo", "a" * 40), ["CodeQL"])

    def test_unbound_context_accepts_only_successful_status(self):
        protection = {"required_status_checks": {"contexts": ["secrets"]}}
        with patch(
            "tools.check_release_candidate.github_json",
            side_effect=[protection, {"check_runs": []}, [{"context": "secrets", "state": "success"}]],
        ):
            self.assertEqual(check_required_statuses("owner/repo", "a" * 40), [])

        with patch(
            "tools.check_release_candidate.github_json",
            side_effect=[protection, {"check_runs": []}, [{"context": "secrets", "state": "pending"}]],
        ):
            self.assertEqual(check_required_statuses("owner/repo", "a" * 40), ["secrets"])


if __name__ == "__main__":
    unittest.main()
