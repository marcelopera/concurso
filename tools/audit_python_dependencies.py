"""Audit the resolved Python runtime, extraction, development, and build dependencies."""

import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "build/security/python-dependencies.json"
PIP_VERSION = "26.2"
PIP_AUDIT_VERSION = "2.10.1"

LOCAL_EDITABLES = {
    "concurso",
    "concurso-contracts",
    "concurso-estudo",
    "concurso-pipeline",
}
REQUIRED_BY_SCOPE = {
    "runtime": {
        "jsonschema",
        "attrs",
        "jsonschema-specifications",
        "referencing",
        "rpds-py",
    },
    "extraction": {"pdfplumber", "pypdf", "pdfminer-six", "pillow", "pypdfium2"},
    "development": {"ruff", "pip-audit"},
    "build": {"pip", "setuptools", "wheel"},
}


def normalize_name(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def validate_audit_report(report, sys_platform=sys.platform):
    """Require all scope sentinels and allow only known local editables to skip."""
    dependencies = report.get("dependencies")
    if not isinstance(dependencies, list):
        raise ValueError("pip-audit JSON has no dependency inventory")
    if not dependencies:
        raise ValueError("pip-audit resolved zero dependencies")

    by_name = {}
    for dependency in dependencies:
        name = normalize_name(dependency.get("name", ""))
        if not name:
            raise ValueError("pip-audit returned a dependency without a name")
        if name in by_name:
            raise ValueError(f"pip-audit returned duplicate dependency: {name}")
        by_name[name] = dependency

    expected_local = {normalize_name(name) for name in LOCAL_EDITABLES}
    skipped = {}
    audited = []
    for name, dependency in by_name.items():
        if "skip_reason" in dependency:
            skipped[name] = dependency["skip_reason"]
            continue
        if "version" not in dependency or not isinstance(dependency.get("vulns"), list):
            raise ValueError(f"pip-audit returned an incomplete dependency record: {name}")
        audited.append(dependency)

    unexpected_skips = set(skipped) - expected_local
    if unexpected_skips:
        raise ValueError(f"unexpected packages skipped by pip-audit: {sorted(unexpected_skips)}")
    if set(skipped) != expected_local:
        missing_local = expected_local - set(skipped)
        raise ValueError(f"local packages must be installed as explicit editables: {sorted(missing_local)}")
    if any(reason != "distribution marked as editable" for reason in skipped.values()):
        raise ValueError(f"local package exclusions changed unexpectedly: {skipped}")
    if not audited:
        raise ValueError("pip-audit resolved zero third-party dependencies")

    audited_names = {normalize_name(dependency["name"]) for dependency in audited}
    required_by_scope = {scope: set(names) for scope, names in REQUIRED_BY_SCOPE.items()}
    if sys_platform == "win32":
        required_by_scope["runtime"].add("tzdata")

    missing = {
        scope: sorted(names - audited_names) for scope, names in required_by_scope.items() if names - audited_names
    }
    if missing:
        details = "; ".join(f"{scope}: {', '.join(names)}" for scope, names in missing.items())
        raise ValueError(f"audited inventory is missing required scope packages ({details})")

    return sorted(audited, key=lambda dependency: normalize_name(dependency["name"]))


def run_checked(command, *, cwd=ROOT):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(map(str, command))}\n{result.stdout}{result.stderr}"
        )
    return result


def audit_environment(venv_path):
    executable = venv_path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run_checked([str(executable), "-m", "pip", "install", "--upgrade", f"pip=={PIP_VERSION}"])
    run_checked([str(executable), "-m", "pip", "install", "setuptools>=77", "wheel>=0.45"])
    run_checked(
        [
            str(executable),
            "-m",
            "pip",
            "install",
            "--no-build-isolation",
            "-e",
            "packages/contracts",
            "-e",
            "packages/pipeline",
            "-e",
            "packages/estudo/backend",
            "-e",
            ".[dev,extract]",
        ]
    )

    auditor = venv_path / ("Scripts/pip-audit.exe" if os.name == "nt" else "bin/pip-audit")
    result = subprocess.run(
        [
            str(auditor),
            "--local",
            "--skip-editable",
            "--format",
            "json",
            "--progress-spinner",
            "off",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    try:
        audit_report = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"pip-audit did not produce valid JSON (exit {result.returncode}): {result.stdout}{result.stderr}"
        ) from error

    audited = validate_audit_report(audit_report)
    local_exclusions = [
        {"name": dependency["name"], "reason": dependency["skip_reason"]}
        for dependency in audit_report["dependencies"]
        if dependency.get("skip_reason")
    ]
    report = {
        "format_version": 1,
        "scanner": {"name": "pip-audit", "version": PIP_AUDIT_VERSION, "vulnerability_service": "PyPI"},
        "environment": {
            "python": platform.python_version(),
            "system": platform.system(),
            "sys_platform": sys.platform,
        },
        "scopes": {
            "runtime": ["packages/contracts", "packages/pipeline", "packages/estudo/backend"],
            "extraction": ["root extra extract -> concurso-pipeline[extract]"],
            "development": ["root extra dev"],
            "build": [f"pip=={PIP_VERSION}", "setuptools>=77", "wheel>=0.45"],
        },
        "audited_dependencies": audited,
        "excluded_local_dependencies": sorted(local_exclusions, key=lambda item: normalize_name(item["name"])),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Audited {len(audited)} third-party Python packages on {sys.platform}.")
    print(f"Inventory: {REPORT_PATH.relative_to(ROOT)}")
    print(f"Explicitly excluded local editables: {', '.join(item['name'] for item in local_exclusions)}")

    if result.returncode:
        print("pip-audit reported vulnerabilities or an audit error; see the inventory above.", file=sys.stderr)
    return result.returncode


def main():
    with tempfile.TemporaryDirectory(prefix="concurso-python-audit-") as temporary_directory:
        environment = Path(temporary_directory) / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        return audit_environment(environment)


if __name__ == "__main__":
    raise SystemExit(main())
