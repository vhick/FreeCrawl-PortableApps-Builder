# Validation, evidence, and supply-chain controls

## Current evidence (builder kit b1r1, 2026-11-09)

| Area | Evidence | Status |
| --- | --- | --- |
| Upstream release/readme, Electron build config, path-handling code and Playwright script | Public source reviewed at stable `v1.1.5` | SOURCE-INSPECTED |
| Shared Package Builder `v1.0.0` | Immutable commit `0112c35580e83b37eb8757ebcb949274e1631a04`; action.yml, scripts/build.ps1, common.ps1, NSIS source reviewed | SOURCE-INSPECTED |
| Shared Release Publisher `v1.1.1` | Immutable commit `cb64f86ac2d8c67506db5832de07f9ff58cbeaeb`; action.yml and scripts/publish.py reviewed | SOURCE-INSPECTED |
| Offline unit tests | Python unittest: version sorting, adapter placement/idempotency, compiled adapter guard, PE architecture, 404-only lookup | STATIC-VALIDATED |
| GitHub Actions YAML and action wiring | Python YAML parse, required manual trigger, action SHA references, 22 ordered steps | STATIC-VALIDATED |
| C++ launcher compilation | Requires a hosted Windows MSVC build; cannot compile with the current Linux-only environment | NOT YET VERIFIED |
| Full upstream TypeScript and Electron build | Requires Windows runner, npm and actual fetched upstream tag | NOT YET VERIFIED |
| Source-built app launch and Data persistence | Requires GUI Windows | NOT YET VERIFIED |
| Electron Chromium and Playwright rendering | Requires GUI Windows and browser download | NOT YET VERIFIED |
| TraceGuard/ShellGuard | Intentionally absent pending proof of additional owned host paths | NOT APPLICABLE / RUNTIME AUDIT PENDING |
| Native Windows notifications and click-to-open | Requires an interactive Windows taskbar/Explorer | NOT YET VERIFIED |
| Actual ZIP output and finished installer | Produced and validated by future GitHub Actions run | NOT YET VERIFIED |
| Installer actual fresh install/upgrade/reinstall | Requires manual Windows installer acceptance | NOT YET VERIFIED |
| Shared publisher dry run and live release publication | Must succeed on GitHub Actions | NOT YET VERIFIED |
| User confirmed runtime portability | Requires an actual user test | NOT YET VERIFIED |

The **builder-kit ZIP** is a different output from the **application ZIP** and installer. The first exists at delivery time and can be tested statically; the latter do not exist unless the workflow has run successfully.

## Supply-chain controls

1. Resolve a *published stable release* only. Reject draft and prerelease versions, and compare versions numerically. No default-main fallback.
2. Resolve the source tag to a full 40-character commit through the GitHub API, fetch exactly that tag, and require the checked-out `git rev-parse HEAD` to match.
3. Require upstream's root package version, desktop package version and MIT license. Record a SHA-256 lockfile digest, then install dependencies with `npm ci` and the upstream-approved `PLAYWRIGHT_SKIP_BROWSER_INSTALL=1` flag. Run `prepare:playwright-bundle` to create the expected resource folder, keeping the upstream default of on-demand Chromium download.
4. Apply a narrow source patch before Electron's single-instance lock and `whenReady`; fail if the upstream anchor has moved or a portability patch is already present. Confirm the adapter occurs in transpiled Electron main JavaScript.
5. Build both application and Windows PE launcher from source. Assert x64 PE headers and actual Electron `resources/app.asar` before creating ZIP.
6. Validate appinfo metadata, original upstream icon resources, CRC, root directory and expected Data/Other layout. Create ZIP independently *before* the shared installer runs.
7. Run only shared installer action from its verified full `v1.0.0` commit; verify actual `.paf.exe` output and copy it to the release payload directory. Preserve the ZIP as an Actions recovery artifact if later steps fail.
8. Run the pinned full-commit publisher's `dry-run=true` before `dry-run=false`. No publication of unvalidated outputs. Releases use this calling repository only; pruning disabled.
9. Do not erase an existing release. A fully matching publisher-owned release identity is skipped, while unrelated/draft/incomplete same-tag releases are rejected.
10. CI checkout does **not** persist the GitHub token in local git config, and no personal access token is necessary.

## Windows / host safety

No registry, Start Menu, Desktop, autostart, COM or taskbar modifications are intentionally made by the wrapper. The copied upstream app and Windows itself may use OS-managed shell caches, Windows error reporting, notification state, and user-approved integration channels. No host-profile harvesting or broad file deletion is attempted. Source redirection is favored because FreeCrawl uses Electron userData/sessionData and a userData-relative Playwright download cache.

Physical Windows acceptance remains necessary for installed-app coexistence, notification registration, crash resilience, empty-directory retention by the shared installer, password/OAuth portability, and data-schema rollback. Document any failures rather than labeling CI completion as full runtime portability.
