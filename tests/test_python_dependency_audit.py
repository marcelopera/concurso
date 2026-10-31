"""Regression guards for the Python dependency audit's scope and local exclusions."""

import unittest

from tools.audit_python_dependencies import LOCAL_EDITABLES, REQUIRED_BY_SCOPE, validate_audit_report


def complete_report(platform="linux"):
    packages = set().union(*REQUIRED_BY_SCOPE.values())
    if platform == "win32":
        packages.add("tzdata")
    dependencies = [{"name": name, "version": "1.0", "vulns": []} for name in sorted(packages)]
    dependencies.extend(
        {"name": name, "skip_reason": "distribution marked as editable"} for name in sorted(LOCAL_EDITABLES)
    )
    return {"dependencies": dependencies, "fixes": []}


class PythonDependencyAuditTests(unittest.TestCase):
    def test_empty_backend_requirements_audit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "resolved zero dependencies"):
            validate_audit_report({"dependencies": [], "fixes": []}, sys_platform="linux")

    def test_runtime_scope_is_required(self):
        report = complete_report()
        report["dependencies"] = [
            dependency for dependency in report["dependencies"] if dependency["name"] != "jsonschema"
        ]

        with self.assertRaisesRegex(ValueError, "runtime: jsonschema"):
            validate_audit_report(report, sys_platform="linux")

    def test_extraction_scope_is_required(self):
        report = complete_report()
        report["dependencies"] = [
            dependency for dependency in report["dependencies"] if dependency["name"] != "pdfplumber"
        ]

        with self.assertRaisesRegex(ValueError, "extraction: pdfplumber"):
            validate_audit_report(report, sys_platform="linux")

    def test_windows_audit_requires_the_conditional_backend_dependency(self):
        with self.assertRaisesRegex(ValueError, "runtime: tzdata"):
            validate_audit_report(complete_report(), sys_platform="win32")

    def test_only_the_four_local_editables_may_be_excluded(self):
        report = complete_report()
        report["dependencies"].append(
            {"name": "third-party-without-version", "skip_reason": "package metadata is incomplete"}
        )

        with self.assertRaisesRegex(ValueError, "unexpected packages skipped"):
            validate_audit_report(report)


if __name__ == "__main__":
    unittest.main()
