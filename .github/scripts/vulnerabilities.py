"""Fail closed on new reachable vulnerabilities and changes to reviewed exceptions."""
import json
import subprocess
from pathlib import Path

EXCEPTIONS = {"GO-2026-4883", "GO-2026-4887"}
DOCKER_MODULE = "github.com/docker/docker"
DOCKER_VERSION = "v28.5.2+incompatible"


def parse_stream(text):
    decoder = json.JSONDecoder()
    records = []
    while text.strip():
        record, end = decoder.raw_decode(text.lstrip())
        records.append(record)
        text = text.lstrip()[end:]
    if not records or records[0].get("config", {}).get("scan_level") != "symbol":
        raise ValueError("Missing symbol-level scan configuration")
    if not any("SBOM" in record for record in records):
        raise ValueError("Missing scan inventory")
    return records


def blocked_findings(records, packages):
    # Both advisories affect the daemon/plugin implementation, not client calls.
    forbidden = (DOCKER_MODULE + "/daemon", DOCKER_MODULE + "/plugin",
                 DOCKER_MODULE + "/pkg/authorization", DOCKER_MODULE + "/api/server")
    client_only = not any(p == prefix or p.startswith(prefix + "/") for p in packages for prefix in forbidden)
    blocked = set()
    reviewed = set()
    for record in records:
        finding = record.get("finding")
        if not finding:
            continue
        frame = finding["trace"][0]
        if not frame.get("function"):
            continue  # Imported/module-only findings are not reachable symbol findings.
        osv = finding["osv"]
        if (osv in EXCEPTIONS and client_only and frame.get("module") == DOCKER_MODULE
                and frame.get("version") == DOCKER_VERSION):
            reviewed.add(osv)
        else:
            blocked.add(osv)
    return blocked, reviewed


def main():
    packages = subprocess.check_output(["go", "list", "-deps", "./..."], text=True).splitlines()
    result = subprocess.run(
        ["go", "tool", "-modfile=.github/tools/go.mod", "govulncheck", "-json", "./..."],
        capture_output=True, text=True, check=True,
    )
    Path("dist").mkdir(exist_ok=True)
    Path("dist/govulncheck.json").write_text(result.stdout)
    blocked, reviewed = blocked_findings(parse_stream(result.stdout), packages)
    print("Reviewed daemon-only advisories:", ", ".join(sorted(reviewed)) or "none")
    print("Unreviewed reachable vulnerabilities:", ", ".join(sorted(blocked)) or "none")
    if blocked:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
