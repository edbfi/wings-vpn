import importlib.util
import unittest
from pathlib import Path


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path("scripts") / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lint = load("lint")


class Gates(unittest.TestCase):
    def issue(self, line="defer file.Close()"):
        return {"Pos": {"Filename": "legacy.go"}, "FromLinter": "errcheck",
                "Text": "unchecked Close", "SourceLines": [line]}

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


if __name__ == "__main__":
    unittest.main()
