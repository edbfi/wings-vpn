# Development validation

Every pull request and default-branch push runs `ci`: hygiene/quality, Linux amd64
and arm64 builds on Go 1.26.8 and 1.27.1, native macOS builds/race tests on both Go
versions, and CodeQL. The shared dispatch guard and fail-closed aggregate require
all expected jobs to succeed. No path filter may bypass this workflow.

Shared actions, workflows and presets use immutable `v3.0.1` references.
Renovate is the sole ongoing dependency merge owner. It merges eligible dependency
PRs by rebasing only after current required CI and policy checks pass. Native
platform automerge stays off. Shared Renovate policy updates remain manual;
release-age rules, holds and repository-specific updater ownership still apply.
The legacy Actions merger and its comment commands are retired.

The separate PR policy workflow verifies Conventional Commit titles, genuine
matching author sign-offs, Renovate provenance, holds, outstanding review requests
and unresolved changes requests. Require its actual emitted policy context alongside
all existing application/content checks, pinned to GitHub Actions, with strict
up-to-date branch protection. Preserve stronger review requirements. Explicit CI
dispatches do not substitute for a missing metadata policy result. Review exact
head/base, full diffs and all required results before a bootstrap merge, then
verify resulting default-branch CI. Repository-specific updater ownership and
manual publication or delivery controls remain unchanged.

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

The lint regression baseline is measured on Linux; run the quality script there.
Native macOS build/race tests are separate. Direct macOS lint currently also
reports SA1019 for the inherited F_GETPATH syscall in internal/ufs/fs_darwin.go;
that platform-specific finding is not suppressed or added to the Linux baseline.

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
integration gaps and the lint backlog remain documented limitations.
Platform checks use stable minimum/current lane names so a Go patch update does
not invalidate required-check names or suppress binary artifacts. The minimum
lane stays on Go 1.26 patches; the current lane may advance to new Go releases.
All existing Linux builds, native macOS/race tests, lint and vulnerability gates
remain required.

The inherited Nix shell still pins a historical nixpkgs/Go 1.22 environment and is
not a supported validation path; use the documented toolchain above. Updating and
validating that optional shell is a remaining tooling gap. The container builder
uses Go 1.27.1 to match the current supported CI lane.

## Publication and upstream sync

Release, container publication and upstream sync remain disabled during migration.
Their stored workflows and credentials are preserved for separate validation.
The self-update command defaults to upstream Pelican; do not use it to update this
fork, because an upstream binary does not contain its network-mode customization.
No fork release has been published.

## Service startup fixture

The required `service` job builds and launches the real Wings executable on
Ubuntu 26.04 amd64 with the runner's real Docker daemon. A loopback-only panel
fixture serves the boot inventory and state-reset endpoints and checks generated
credentials. The test requires authenticated system metadata, the empty server
listing, rejection of unauthenticated requests, an SSH/SFTP banner and an observed
panel reset. A second startup with malformed panel JSON must exit nonzero for the
expected configuration-load error before reaching readiness.

Each run owns a unique internal Docker network, temporary state/config/log paths,
ephemeral API/SFTP ports and a process group. It uses the existing rootless-user
configuration to avoid system account changes, disables host log rotation and
removes all temporary resources on success, failure and handled cancellation.
Tokens are generated locally, checked against daemon logs and redacted from
failure output. No log/config artifacts are uploaded. Hard runner termination
relies on GitHub disposing of the runner.

Run `go build -mod=readonly -o dist/wings-service .` followed by
`python3 .github/scripts/service-smoke.py dist/wings-service` on a disposable Linux
machine with Docker access. There is no skip path when prerequisites are missing.
This proves daemon startup and real Docker connectivity with a simulated panel;
game-container launch, VPN routing, privileged user creation and full authenticated
SFTP transfers remain separate coverage. Existing CLI/native/race/CodeQL checks
remain mandatory. The aggregate directly requires the service job.
