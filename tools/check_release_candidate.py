"""Read-only gate for a release SHA; never creates or publishes refs."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Keep the path policy aligned with docs/history-cleanup.md and
# tools/history_cleanup_plan.py without depending on that planner's API.
PRIVATE_HISTORY_PATH = re.compile(
    r"^(?:base-questoes/|biblioteca-concursos/|sistema-estudo/dados/)|"
    r"(?:^|/)(?:execucoes|fontes-visuais|revisao-visual|piloto-[^/]+|evidencias[^/]*)(?:/|$)|"
    r"\.(?:pdf|png|jpe?g|log|sqlite(?:-wal|-shm)?)$",
    re.IGNORECASE,
)
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class GateError(Exception):
    """A release precondition could not be verified."""


def run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)
    if result.returncode:
        raise GateError(f"Command failed: {args[0]}")
    return result.stdout.strip()


def repository_slug(root: Path) -> str:
    remote = run("git", "config", "--get", "remote.origin.url", cwd=root)
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", remote)
    if not match:
        raise GateError("origin must point to a GitHub repository")
    return match.group(1)


def github_json(endpoint: str) -> Any:
    result = subprocess.run(["gh", "api", endpoint], check=False, capture_output=True, text=True)
    if result.returncode:
        raise GateError(f"GitHub API request failed: {endpoint}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GateError(f"GitHub API returned invalid JSON: {endpoint}") from exc


def evidence_file(path: Path, repo_root: Path, label: str) -> None:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        pass
    else:
        raise GateError(f"{label} must be stored outside the repository")
    if not resolved.is_file() or resolved.stat().st_size == 0:
        raise GateError(f"{label} is missing or empty")


def matching_paths(sha: str, repo_root: Path) -> int:
    result = subprocess.run(
        ["git", "-c", "core.quotePath=false", "log", "-z", "--format=", "--name-only", sha],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        raise GateError("Could not inspect the candidate commit history")
    names = (name.decode("utf-8", errors="surrogateescape") for name in result.stdout.split(b"\0"))
    return sum(1 for name in names if name and PRIVATE_HISTORY_PATH.search(name))


def check_required_statuses(repository: str, sha: str) -> list[str]:
    protection = github_json(f"repos/{repository}/branches/main/protection")
    status_policy = protection.get("required_status_checks")
    required = status_policy.get("checks") if status_policy else None
    if status_policy and required is None:
        required = [{"context": context, "app_id": None} for context in status_policy.get("contexts", [])]
    if not required:
        raise GateError("main has no readable required status-check list")

    check_runs = github_json(f"repos/{repository}/commits/{sha}/check-runs?per_page=100").get("check_runs", [])
    statuses = github_json(f"repos/{repository}/commits/{sha}/statuses?per_page=100")
    failed = []
    for check in required:
        context = check["context"]
        expected_app = check.get("app_id")
        named_runs = [item for item in check_runs if item["name"] == context]
        if expected_app is not None:
            runs = [item for item in named_runs if item.get("app", {}).get("id") == expected_app]
            if not runs:
                failed.append(context)
                continue
        else:
            runs = named_runs
        if runs:
            latest = max(runs, key=lambda item: item["id"])
            if latest.get("status") != "completed" or latest.get("conclusion") != "success":
                failed.append(context)
            continue

        latest_status = next((item for item in statuses if item["context"] == context), None)
        if not latest_status or latest_status.get("state") != "success":
            failed.append(context)
    return failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sha", help="Full 40-character SHA at the protected main HEAD")
    parser.add_argument(
        "--backup-evidence", required=True, type=Path, help="Non-empty proof stored outside the repository"
    )
    parser.add_argument(
        "--cleanup-evidence", required=True, type=Path, help="Non-empty proof stored outside the repository"
    )
    parser.add_argument(
        "--confirm-no-private-assets",
        required=True,
        action="store_true",
        help="Confirm the release payload contains no private data or assets",
    )
    args = parser.parse_args()

    try:
        if not FULL_SHA.fullmatch(args.sha):
            raise GateError("provide the full 40-character lowercase commit SHA")
        root = Path(run("git", "rev-parse", "--show-toplevel")).resolve()
        head = run("git", "rev-parse", "HEAD", cwd=root)
        if head != args.sha:
            raise GateError("checkout HEAD does not match the requested SHA")
        if run("git", "status", "--porcelain", cwd=root):
            raise GateError("working tree is not clean")
        run("git", "cat-file", "-e", f"{args.sha}^{{commit}}", cwd=root)

        repository = repository_slug(root)
        main_sha = github_json(f"repos/{repository}/commits/main")["sha"]
        if main_sha != args.sha:
            raise GateError("requested SHA is not the current remote main HEAD")

        path_count = matching_paths(args.sha, root)
        if path_count:
            raise GateError(
                f"{path_count} historical path entries match the private-data cleanup policy; review history before release"
            )
        evidence_file(args.backup_evidence, root, "backup evidence")
        evidence_file(args.cleanup_evidence, root, "cleanup evidence")

        failed = check_required_statuses(repository, args.sha)
        if failed:
            raise GateError("required checks are missing or not successful: " + ", ".join(failed))
    except GateError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1

    print(f"PRECHECK PASSED: {args.sha} is the remote main head; known history paths and required checks passed.")
    print(
        "Evidence files are present and the no-private-assets flag was supplied; review their contents before release."
    )
    print("This read-only check does not create or publish a tag or release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
