# Upstream audit snapshot (2026-11-09)

Repository: https://github.com/kemalai/FreeCrawl-SEO-Tool

Latest **observed** published stable release: `v1.1.5` (November 7, 2026), short linked source commit `82a980e`. A complete 40-digit commit and lockfile hash will be resolved, verified and written into `work/identity.json` during each Actions run. A snapshot cannot guarantee the newest version when the workflow eventually runs.

Framework: Electron 41 (config pins 41.2.2), TypeScript, Node.js 22+, React 19, electron-vite 5, electron-builder 26, npm workspaces and `package-lock.json`. Source: MIT (Copyright 2026 Kemal Acar). Windows target: x64. Build source into `win-unpacked` using documented `electron-builder --win --dir`, not the installer or single-file upstream portable asset. The upstream `electron-builder.yml` includes optional bundled Playwright browsers, but this builder defaults to on-demand browsers in Data to avoid a large predownload.

| Finding | Evidence (source inspected) | File/registry path | Responsible component | PORTABLEAPPS remedy | Data safety | Functionality effect | Test | Limit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Preferences file | `apps/desktop/src/main/index.ts` `prefsFilePath()` (~1443) | `app.getPath('userData')/preferences.json` | FreeCrawl | Early `app.setPath('userData',Data/Profile)` | No host deletion | None intended | Settings, restart | Needs GUI test |
| Project scratch SQLite/WAL | `index.ts` `defaultScratchPath/newWorkingDbPath()` (~2450-2519) | `<userData>/projects/*.seoproject*` | FreeCrawl + node:sqlite | Same early userData redirect | Preserves live DB and Data | None intended | Crawl, crash, repeat | DB schema rollback not guaranteed |
| Logs/debug | `index.ts` `logger.initFileLogging` (~11144), `debug.txt` | `<userData>/debug.txt`; Electron logs path | FreeCrawl/Electron | userData, logs and crashDumps set to Data | No log harvesting | Logging retained | Launch and errors | Windows Event Log outside app control |
| Playwright Chromium | `apps/desktop/src/main/playwright-setup.ts` `installTargetDir()` (~115), env override (~126) | `<userData>/playwright-browsers`; `PLAYWRIGHT_BROWSERS_PATH` | FreeCrawl/Playwright | Root launcher sets env + early userData redirect | Downloads stay in Data | JS rendering remains available | Browser install + render | Browser large; needs network initially |
| Chromium session | Electron `sessionData` API (Electron 41.2.2) | Native Electron session paths | Electron | Early `app.setPath('sessionData',Data/Session)` | No host cleanup | Caches and cookies retained | First and second launch | Runtime confirmation required |
| Temporary PDF/export project files | `index.ts` ~2865,7756,9515 | `app.getPath('temp')` | FreeCrawl | Child-scoped TEMP/TMP pointing `Data/Temp` | No global environment mutation | May consume portable storage | Temp file and PDF test | OS-managed temp may still be used by children |
| User-chosen saved projects | `index.ts` default `app.getPath('documents')` (~3029), export dirs (~10373) | Documents / chosen location | User action, FreeCrawl UI | **Preserve explicit user choice**, no auto-move | Protects outside user files | No default-path semantic change | Dialog/save | Exports are deliberately external |
| Update download | `index.ts` `downloadAndRevealInstaller` (~3553), manual update (~3646) | User Downloads | FreeCrawl | Warn to use builder instead of downloaded Setup | No auto-install | Update check remains available | Menu check | Setup download is not a portable upgrade |
| Second-instance / multiwindow | `index.ts` `requestSingleInstanceLock` (~11042) | Electron userData instance lock | Electron/FreeCrawl | Keep native app behavior, launcher waits | Prevents DB racing if launched correctly | Multiwindow preserved | Two launches | Needs GUI test |
| File associations | `apps/desktop/electron-builder.yml` fileAssociations (~95) | Windows shell, installer-dependent | electron-builder installer | **Do not run upstream installer or register association** | Preserves installed file associations | Double-click association absent | Registry diff | Intentional tradeoff |
| Shell/toasts/tray | `index.ts` imports `Notification`, `Tray`; no verified owned registration path at this snapshot | Potential Windows-managed toast/AUMID state | Electron/Windows | No speculative ShellGuard deletion | Protect installed apps | Notifications not disabled | ProcMon + click-to-open | Requires actual test |
| App startup pre-init storage | `index.ts` single-instance lock (~11042), `whenReady()` (~11144) | Core userData and session paths | Electron | Insert adapter before lock, readiness and Playwright setup | No harvesting | None intended | Source regression + runtime | Future upstream changes fail closed |

**Finding status:** Source-inspected and API-doc-supported, **not** runtime-observed in this environment. No app-specific registry/shortcut writes were verified; collecting or deleting arbitrary same-name host entries would be unsafe. Windows shell caches, protected credential stores and actual notification side effects require separate interactive validation.

Source references:
- https://raw.githubusercontent.com/kemalai/FreeCrawl-SEO-Tool/v1.1.5/apps/desktop/src/main/index.ts
- https://raw.githubusercontent.com/kemalai/FreeCrawl-SEO-Tool/v1.1.5/apps/desktop/src/main/playwright-setup.ts
- https://raw.githubusercontent.com/kemalai/FreeCrawl-SEO-Tool/v1.1.5/apps/desktop/electron-builder.yml
- https://raw.githubusercontent.com/kemalai/FreeCrawl-SEO-Tool/v1.1.5/package.json
- https://raw.githubusercontent.com/kemalai/FreeCrawl-SEO-Tool/v1.1.5/LICENSE
- https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/action.yml
- https://raw.githubusercontent.com/vhick/portable-release-publisher/v1.1.1/action.yml

**Not audited exhaustively:** Entire upstream 1M+ lines of cross-workspace code, all nested dependency subprocess paths, notification registrations on a physical Windows machine, cryptographic signature provenance. The tested build stage should block upstream structural changes; additional runtime discoveries require a reviewed new kit revision.
