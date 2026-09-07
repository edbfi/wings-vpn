# Development validation

Every pull request and default-branch push runs `ci`: hygiene/quality, Linux amd64
and arm64 builds on Go 1.26.8 and 1.27.1, native macOS builds/race tests on both Go
versions, and CodeQL. The shared dispatch guard and fail-closed aggregate require
all expected jobs to succeed. Require `ci / required`, strict up-to-date branches
and no bypasses. No path filter may bypass this workflow.

Go 1.26 is now the minimum: `golang.org/x/crypto` 0.56.0 requires it and fixes the
reported SSH deadlocks/source-address validation issues. Its compatible x/text
update also removes the reported malformed-input infinite loop. The runtime
module stays separate from developer tools in `.github/tools/go.mod`; tools run
with Go 1.27.1 via `go tool -modfile=.github/tools/go.mod <tool>`.

Local commands:

- `prek run --all-files`: hygiene, secret scanning, gofumpt, the lint regression
  gate and the Linux build. The branch-protection hook is local-only in CI.
- `bash .github/scripts/quality.sh`: read-only gofumpt, module verification,
  Python compilation/gate tests, golangci-lint and reachable-vulnerability checks.
- `go test -race ./...`: existing filesystem, backup, HTTP, server, SFTP and
  concurrency suites. The Linux build also runs tests with CGO disabled.

The complete standard golangci-lint set is enabled. Its initial 203 diagnostics
are recorded by exact path, linter, message, source text and multiplicity in
`.github/lint-baseline.json`. New or duplicated findings fail; existing findings
remain visible in the count. This includes legacy mutex-copy/error-handling
issues and is a tracked backlog, not a claim of clean lint. Remove baseline
entries when repairing them. Formatting has one separate gofumpt baseline commit.

`govulncheck` fails on all unreviewed reachable findings. The two narrow exceptions
are GO-2026-4883 and GO-2026-4887, only for Docker module v28.5.2+incompatible and
only while the dependency graph excludes daemon, plugin, authorization and API
server packages. The Go database applies these unreviewed advisories to the whole
legacy module; upstream identifies Docker Engine plugin bugs. Wings links the
client, not the daemon implementations. Changing the module version or importing
those packages invalidates the exception. The raw report is retained in `dist/`.
This does not validate or patch the Docker Engine installed on a deployment host.

Sources: [AuthZ advisory](https://github.com/moby/moby/security/advisories/GHSA-x744-4wpc-v9h2),
[plugin privilege advisory](https://github.com/moby/moby/security/advisories/GHSA-pxq6-2prw-chj9),
[Go database scope](https://pkg.go.dev/vuln/GO-2026-4887),
[golangci-lint configuration](https://golangci-lint.run/docs/configuration/file/).

Upstream sync now uses PRs for both clean and conflicted merges, resolves the
upstream/default branches from Git metadata, deduplicates existing sync PRs and
explicitly dispatches CI for the exact commit. Optional existing SYNC_PAT and
NanoGPT configuration is preserved; clean merges never call the paid model.
Trusted helper scripts are copied before merging upstream. Conflict markers and
unresolved code fail ordinary CI. Enable Actions to create PRs; the repository
token needs Contents/Pull requests/Issues/Actions write only for this writer.
No default-branch push or protection bypass is needed.

Tag releases validate source before publishing draft artifacts; their version
comes from existing build flags, so the redundant source-writing release branch
is removed. Container publication keeps the repository's own GHCR namespace and
existing release/manual controls. Platform CI does not start Docker containers,
configure VPNs, install games, contact NanoGPT, or exercise a live panel. These
integration gaps and the lint backlog keep Go/container automerge disabled;
Renovate still groups and proposes updates through the shared versioned preset.

The inherited Nix shell still pins a historical nixpkgs/Go 1.22 environment and is
not a supported validation path; use the documented toolchain above. Updating and
validating that optional shell is a remaining tooling gap. The container builder
uses Go 1.27.1 to match the current supported CI lane.
