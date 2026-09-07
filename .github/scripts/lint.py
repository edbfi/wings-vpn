"""Reject new diagnostics without concealing the inherited lint backlog."""
import collections
import json
import subprocess
from pathlib import Path


def issue_key(issue):
    return json.dumps([
        issue["Pos"]["Filename"], issue["FromLinter"], issue["Text"],
        [line.strip() for line in issue["SourceLines"]],
    ], separators=(",", ":"))


def compare(issues, baseline):
    current = collections.Counter(issue_key(issue) for issue in issues)
    allowed = collections.Counter(baseline)
    return current - allowed


def main():
    result = subprocess.run(
        ["go", "tool", "-modfile=.github/tools/go.mod", "golangci-lint", "run"],
        capture_output=True, text=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr or result.stdout)
    # The tool appends a human issue-count summary after its JSON object.
    report, end = json.JSONDecoder().raw_decode(result.stdout)
    tail = result.stdout[end:].strip()
    if tail and not all(line.endswith("issues:") or line.startswith("* ") for line in tail.splitlines()):
        raise RuntimeError(f"Unexpected linter output: {tail}")
    issues = report["Issues"] or []
    if result.returncode == 1 and not issues:
        raise RuntimeError("Linter failed without diagnostic records")
    baseline = json.loads(Path(".github/lint-baseline.json").read_text())
    new = compare(issues, baseline["diagnostics"])
    print(f"{len(issues)} existing Go lint diagnostics; {sum(new.values())} new diagnostics")
    for issue, count in new.items():
        print(f"{count}x {issue}")
    if new:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
