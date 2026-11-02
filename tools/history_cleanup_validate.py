"""Validate a rewritten mirror against a private history-cleanup plan."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from history_cleanup_common import reject_path_inside_git_repository
from history_cleanup_mailmap import validate_applied_mailmap
from history_cleanup_plan import current_tree_summary, history_paths, repository_refs


def git(repository: Path, *arguments: str, binary: bool = False):
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        check=True,
        text=not binary,
        encoding=None if binary else "utf-8",
    )
    return result.stdout


def object_storage_bytes(repository: Path) -> int:
    values = {}
    for line in git(repository, "count-objects", "-v").splitlines():
        key, value = line.split(":", 1)
        if key in {"size", "size-pack"}:
            values[key] = int(value.strip())
    return (values.get("size", 0) + values.get("size-pack", 0)) * 1024


def validate(repository: Path, baseline: dict, mailmap_path: Path) -> dict:
    repository = repository.resolve(strict=True)
    git(repository, "rev-parse", "--git-dir")
    if not isinstance(baseline, dict) or baseline.get("version") != 2:
        raise ValueError("Plano de base incompatível; gere-o com a versão atual da ferramenta.")

    before_refs = {entry["ref"]: entry for entry in baseline["refs_before"]}
    after_refs = {entry["ref"]: entry for entry in repository_refs(repository)}
    comparisons = []
    for name in sorted(before_refs.keys() | after_refs.keys()):
        before = before_refs.get(name)
        after = after_refs.get(name)
        if before is None:
            status = "new"
        elif after is None:
            status = "missing"
        elif before["object"] == after["object"] and before.get("peeled") == after.get("peeled"):
            status = "unchanged"
        else:
            status = "rewritten"
        comparisons.append(
            {
                "ref": name,
                "before_object": before["object"] if before else None,
                "after_object": after["object"] if after else None,
                "before_peeled": before.get("peeled") if before else None,
                "after_peeled": after.get("peeled") if after else None,
                "status": status,
            }
        )

    paths = history_paths(repository)
    remove_paths = set(baseline.get("remove_paths", []))
    review_paths = {entry["path"] for entry in baseline.get("review_paths", [])}
    reviewed_keep_paths = set(baseline.get("reviewed_keep_paths", []))
    unresolved_review_paths = set(baseline.get("unresolved_review_paths", []))
    remaining_remove = remove_paths & paths
    remaining_unreviewed = (review_paths & paths) & unresolved_review_paths
    invalid_keep_decisions = reviewed_keep_paths - review_paths

    fsck = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "fsck",
            "--full",
            "--no-reflogs",
            "--unreachable",
            "--no-progress",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    unreachable_count = sum(
        1 for line in fsck.stdout.splitlines() if line.startswith("unreachable ") or line.startswith("dangling ")
    )
    shallow = git(repository, "rev-parse", "--is-shallow-repository").strip() == "true"
    tree_after = current_tree_summary(repository, baseline["base_ref"], remove_paths)
    tree_before = baseline["current_tree_before"]
    tree_preserved = (
        tree_before["preserved_files"] == tree_after["preserved_files"]
        and tree_before["preserved_digest"] == tree_after["preserved_digest"]
    )

    storage_before = int(baseline["object_storage_before_bytes"])
    storage_after = object_storage_bytes(repository)
    reduction = storage_before - storage_after
    reduction_percent = round(reduction * 100 / storage_before, 2) if storage_before else None
    ref_set_unchanged = before_refs.keys() == after_refs.keys()
    mailmap = validate_applied_mailmap(repository, mailmap_path)
    checks = {
        "complete_clone": not shallow,
        "refs_preserved": ref_set_unchanged,
        "no_planned_paths_remain": not remaining_remove,
        "ambiguous_paths_resolved": not unresolved_review_paths,
        "reviewed_keep_decisions_valid": not invalid_keep_decisions,
        "owner_mailmap_applied": mailmap["passed"],
        "preserved_current_tree_matches": tree_preserved,
        "git_fsck": fsck.returncode == 0,
        "no_unreachable_objects": unreachable_count == 0,
    }
    return {
        "version": 1,
        "repository_is_shallow": shallow,
        "refs_before_count": len(before_refs),
        "refs_after_count": len(after_refs),
        "refs": comparisons,
        "paths": {
            "planned_remove_count": len(remove_paths),
            "remaining_remove_count": len(remaining_remove),
            "ambiguous_review_count": len(review_paths),
            "unresolved_review_count": len(unresolved_review_paths),
            "unreviewed_review_paths_remaining": len(remaining_unreviewed),
        },
        "current_tree": {
            "before_preserved_files": tree_before["preserved_files"],
            "after_preserved_files": tree_after["preserved_files"],
            "preserved_digest_matches": tree_preserved,
            "removed_files_from_base_tree_before": tree_before["removable_files"],
            "removed_files_from_base_tree_after": tree_after["removable_files"],
        },
        "objects": {
            "storage_before_bytes": storage_before,
            "storage_after_bytes": storage_after,
            "reduction_bytes": reduction,
            "reduction_percent": reduction_percent,
            "unreachable_objects": unreachable_count,
        },
        "mailmap": {
            "mapped_identity_count": mailmap["mapped_identity_count"],
            "source_identities_remaining": mailmap["source_identities_remaining"],
            "canonical_identity_present": mailmap["canonical_identity_present"],
        },
        "git_fsck_return_code": fsck.returncode,
        "checks": checks,
        "passed": all(checks.values()),
    }


def write_report(path: Path, report: dict, repository: Path) -> None:
    path = reject_path_inside_git_repository(path, repository, "O relatório privado")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as destination:
        json.dump(report, destination, ensure_ascii=False, indent=2)
        destination.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path, help="Clone completo novo dos refs resultantes.")
    parser.add_argument("baseline", type=Path, help="Plano privado criado antes da reescrita.")
    parser.add_argument("--mailmap", required=True, type=Path, help="Mailmap privado usado na reescrita.")
    parser.add_argument("report", type=Path, help="Relatório privado; criado sem sobrescrita.")
    args = parser.parse_args()
    try:
        repository = args.repository.resolve(strict=True)
        baseline_path = reject_path_inside_git_repository(
            args.baseline.resolve(strict=True), repository, "O plano privado"
        )
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        report = validate(repository, baseline, args.mailmap)
        write_report(args.report, report, repository)
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(
        "Validação "
        f"{'aprovada' if report['passed'] else 'reprovada'}: "
        f"{report['refs_after_count']} refs, "
        f"{report['paths']['remaining_remove_count']} caminhos proibidos remanescentes, "
        f"redução medida de {report['objects']['reduction_bytes']} bytes."
    )
    if not report["passed"]:
        failed = [name for name, passed in report["checks"].items() if not passed]
        print("Critérios pendentes: " + ", ".join(failed), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
