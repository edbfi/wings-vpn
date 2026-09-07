import importlib.util
import json
import unittest
from pathlib import Path


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(".github/scripts") / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lint = load("lint")
vuln = load("vulnerabilities")


class Gates(unittest.TestCase):
    def issue(self, line="defer file.Close()"):
        return {"Pos": {"Filename": "legacy.go"}, "FromLinter": "errcheck",
                "Text": "unchecked Close", "SourceLines": [line]}

    def finding(self, osv="GO-2026-4883", version="v28.5.2+incompatible"):
        return {"finding": {"osv": osv, "trace": [{"module": vuln.DOCKER_MODULE,
                 "version": version, "function": "Client.Close"}]}}

    def test_existing_diagnostic_can_move_but_not_multiply(self):
        issue = self.issue()
        baseline = {lint.issue_key(issue): 1}
        self.assertFalse(lint.compare([issue], baseline))
        self.assertTrue(lint.compare([issue, issue], baseline))

    def test_changed_source_and_message_are_new_findings(self):
        issue = self.issue()
        baseline = {lint.issue_key(issue): 1}
        self.assertTrue(lint.compare([self.issue("defer other.Close()")], baseline))
        changed = {**issue, "Text": "a different error"}
        self.assertTrue(lint.compare([changed], baseline))

    def test_fixed_diagnostics_do_not_require_reintroducing_them(self):
        self.assertFalse(lint.compare([], {lint.issue_key(self.issue()): 1}))

    def test_scan_rejects_missing_or_invalid_inventory(self):
        for text in ("", "not json", json.dumps({"config": {"scan_level": "module"}}),
                     json.dumps({"config": {"scan_level": "symbol"}})):
            with self.subTest(text=text), self.assertRaises(ValueError):
                vuln.parse_stream(text)

    def test_reviewed_client_only_findings_are_reported(self):
        self.assertEqual(vuln.blocked_findings([self.finding()], [vuln.DOCKER_MODULE + "/client"]),
                         (set(), {"GO-2026-4883"}))

    def test_new_advisory_or_changed_dependency_blocks(self):
        for finding in (self.finding(osv="GO-2099-9999"), self.finding(version="v29.0.0")):
            blocked, _ = vuln.blocked_findings([finding], [vuln.DOCKER_MODULE + "/client"])
            self.assertTrue(blocked)

    def test_daemon_or_plugin_import_invalidates_exceptions(self):
        for suffix in ("daemon", "daemon/config", "plugin", "pkg/authorization", "api/server/router"):
            blocked, _ = vuln.blocked_findings([self.finding()], [vuln.DOCKER_MODULE + "/" + suffix])
            self.assertEqual(blocked, {"GO-2026-4883"})

    def test_module_only_findings_are_distinct_from_reachable_symbols(self):
        finding = self.finding(osv="GO-2099-9999")
        del finding["finding"]["trace"][0]["function"]
        self.assertEqual(vuln.blocked_findings([finding], []), (set(), set()))


if __name__ == "__main__":
    unittest.main()
