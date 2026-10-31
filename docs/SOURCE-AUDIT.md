# Source-based portability audit — FreeCrawl SEO Tool

Snapshot reviewed: **upstream stable tag `v1.1.1`** (public release dated October 25, 2026). Every GitHub Actions run resolves the newest eligible stable release again. Nonrelease `main` content can differ.

| Behavior | Evidence in upstream source | Portable handling / limitation |
|---|---|---|
| Electron app/build | `apps/desktop/package.json` build:win and Electron 41; `electron-builder.yml` has NSIS and portable | `electron-builder --win --x64 --dir` delivers unpacked Windows application, not upstream setup/portable self-extractor |
| Node and dependencies | root `package.json`: Node >=22.13.0, npm workspaces, TS build | Node 22; npm ci; npm run build |
| Preferences | `apps/desktop/src/main/index.ts` `prefsFilePath()` uses `join(app.getPath('userData'), 'preferences.json')` | `app.setPath('userData', Data/Profile)` before ready |
| SQLite working DBs | same `index.ts` default is `userData/projects/default.seoproject`, scratch `work-*.seoproject`, window/agent sessions | `Data/Profile/projects/` with original cleanup semantics |
| Log files | `apps/desktop/src/main/logger.ts` uses `join(baseDir, 'logs')`; main calls `logger.initFileLogging(app.getPath('userData'))` | `Data/Profile/logs/` |
| Freeze watchdog | `apps/desktop/src/main/index.ts`: `join(app.getPath('userData'), 'debug.txt')` | `Data/Profile/debug.txt` |
| Browser/cache | `apps/desktop/src/main/playwright-setup.ts` checks explicit `PLAYWRIGHT_BROWSERS_PATH`, or `userData/playwright-browsers` | C++ launcher sets path to `Data/Profile/playwright-browsers` |
| Chromium session data | Electron session data uses separate sessionData path | Explicit `app.setPath('sessionData', Data/Profile/Chromium)` before ready |
| Scratch reports | `index.ts` uses `app.getPath('temp')` for PDF/temporary encrypted project files | Patch redirects Electron `temp` to `Data/Temp`; launcher changes TEMP/TMP for child only |
| Exports/projects | `index.ts` uses `app.getPath('documents')` or saved `projectSaveDir`/`exportDir` | User-selected Documents/export paths remain host paths by design |
| Single instance | `index.ts` `app.requestSingleInstanceLock()` and 'second-instance' windows | Preserve, no second concurrent Electron instance writing same caches |
| File associations | `electron-builder.yml`: `fileAssociations` entry for `.seoproject` | Not registered in directory build. Association only when installer installs/registers it |
| Login/registry/services | Main file inspection found no `app.setLoginItemSettings`, `setAsDefaultProtocolClient`, `reg.exe`, `HKEY_`; builder performs no registry or service writes | Cannot prove absence throughout all transitive packages or runtime Windows internals; test host traces manually |
| MCP bridge | `index.ts` runs localhost MCP bridge using `userDataDir: app.getPath('userData')` | Bridge data stays under Data/Profile; localhost network/listen activity is not a file-system portability problem |
| Official license | root `LICENSE`: MIT, 2026 Kemal Acar | Copy license unchanged to `Other/Source` |
| Package icon | `apps/desktop/resources/icon.ico` plus `src/main/assets/window-icon.png` | Reuse upstream branding, create required icon sizes |

## Limitations and corrections

* An Electron Builder `Windows-Portable.exe` is a self-extracting **portable executable distribution**, not proof of userData redirection. We build unpacked Electron binaries and patch profile paths instead.
* User-selected `Documents` and exports are not forced into `Data`. They may still be on the host and may contain absolute paths after moving drives.
* Windows Recent Files, prefetch, crash-reporting, credential stores, DNS cache and external services are outside the builder's control. A truly zero-trace Windows application cannot be established by static code review alone.
* OAuth and integrations using OS-protected credentials can be account/machine-bound. We do not attempt password extraction or risky registry manipulation.
* Source-backed Windows registry keys for user settings were **not confirmed** by the inspected application main/configuration paths. Do not assume nonexistent or invent HKCU/HKLM paths.
* The upstream prebuilt release might contain other assets/dependencies. Our source build uses npm-lockfile versions and the project's Electron Builder configuration, not its prebuilt executable.
* Revision r2 adds authentic `.paf.exe` generation through the checksum-verified PortableApps.com Installer 3.9.22, plus simulated clean-install and upgrade tests on the Windows runner. This is an independent build and is not PortableApps.com-certified. The selected user-owned publisher must have new PAF support pushed to GitHub, as the public v1.0.1 ref remains ZIP-only.

## Source reference URLs

- https://github.com/kemalai/FreeCrawl-SEO-Tool/releases
- https://raw.githubusercontent.com/kemalai/FreeCrawl-SEO-Tool/v1.1.1/package.json
- https://raw.githubusercontent.com/kemalai/FreeCrawl-SEO-Tool/v1.1.1/apps/desktop/package.json
- https://raw.githubusercontent.com/kemalai/FreeCrawl-SEO-Tool/v1.1.1/apps/desktop/electron-builder.yml
- https://raw.githubusercontent.com/kemalai/FreeCrawl-SEO-Tool/v1.1.1/apps/desktop/src/main/index.ts
- https://raw.githubusercontent.com/kemalai/FreeCrawl-SEO-Tool/v1.1.1/apps/desktop/src/main/logger.ts
- https://raw.githubusercontent.com/kemalai/FreeCrawl-SEO-Tool/v1.1.1/apps/desktop/src/main/playwright-setup.ts
- https://raw.githubusercontent.com/kemalai/FreeCrawl-SEO-Tool/v1.1.1/LICENSE
- https://raw.githubusercontent.com/vhick/portable-release-publisher/v1.0.1/action.yml
- https://raw.githubusercontent.com/vhick/portable-release-publisher/v1.0.1/scripts/publish.py
