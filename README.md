# FreeCrawl SEO Tool — independent PortableApps community builder b1r1

**Selected mode: PORTABLEAPPS only.** This is a complete standalone *builder repository* kit. GitHub Actions downloads a **verified stable upstream source tag**, builds a modified Electron desktop application, compiles a real C++ Windows x64 root launcher, makes an independently checked ZIP, invokes **vhick/Portable-Package-Builder v1.0.0** (immutable commit pin) for an independent custom-NSIS PortableApps-**style** installer, then invokes **vhick/portable-release-publisher v1.1.1** (immutable commit pin) for dry-run verification and optional release publication. No upstream fork, local compiler, paid GitHub runner, external custom builder, or private script is required.

**Important:** The ZIP you downloaded containing this README is the **builder kit**, not a finished app. The portable application ZIP and `.paf.exe` are produced later by **Actions** on Windows. Community NSIS output is NOT an officially certified PortableApps.com installer. Native portable mode is not included.

## Beginner's setup using GitHub Desktop

1. On GitHub, select **New repository**. Name it `FreeCrawl-PortableApps-Builder` (or another name). Keep this separate from the original FreeCrawl project. Choose public or private; Releases inherit your repository visibility.
2. Open **GitHub Desktop** and clone that newly created repository. You do **not** need the command line or `git init`.
3. In GitHub Desktop select **Repository → Show in Explorer**. Extract this complete builder kit into that folder, including the otherwise hidden **`.github`** folder. Check `.github/workflows/build-portableapps.yml` exists.
4. Back in GitHub Desktop, review the files and enter commit summary **`Add FreeCrawl PortableApps source builder b1r1`**. Click **Commit to main**, then **Push origin**.
5. On GitHub open your builder repository → **Actions**. If needed, enable Actions. Select **Build FreeCrawl SEO Tool PortableApps** → **Run workflow**.
6. Leave **version = latest**, **package_revision = b1r1**, and **publish = true** for the normal build. `latest` means the newest non-draft, non-prerelease *published semantic-version release*. Set an exact stable version (such as `1.1.5`) to reproduce a previous version.
7. Click **Run workflow**. Review each step. The Actions build checks the upstream tag and full commit, npm lock hash, patches the source, builds the app, compiles the launcher, validates a ZIP, creates and checks the NSIS package, previews the publication, then publishes both files.
8. In your **builder repository**, open **Releases**. Download the generated ZIP for simple extraction, or the `.paf.exe` for the PortableApps Platform. The publisher also publishes a `SHA256SUMS.txt` file. Check the download hash if desired.
9. For ZIP: extract the entire `FreeCrawlSEOToolPortable` directory to a writable folder, for example a USB drive. Double-click **`FreeCrawlSEOToolPortable.exe`** in the root (not the internal `App/FreeCrawl/FreeCrawl SEO Tool.exe`). For PortableApps Platform: use the community `.paf.exe`, then refresh the Platform application menu if necessary.
10. **To update**, exit FreeCrawl and all child/browser processes; back up the *entire* `Data` directory; install the new package over the existing portable folder, or copy just `App`, `Other`, and the root launcher from the new ZIP, **never replace/delete your Data**. The shared community installer is designed to preserve Data, but verify that on your own Windows PC. To roll back, restore the older program files while retaining a backup of new Data (new schema versions might be incompatible).

With **publish = false**, successful results are available under **Actions → the completed workflow → Artifacts**, retained for seven days. If packaging fails after ZIP creation, the validated ZIP is uploaded as a short-lived recovery artifact; **installer generation is still a failure**.

## Mode and portable directory

```text
FreeCrawlSEOToolPortable/
  FreeCrawlSEOToolPortable.exe          Compiled GUI launcher (x64)
  App/
    FreeCrawl/                          Source-built Electron win-unpacked application
      FreeCrawl SEO Tool.exe
      resources/app.asar
    AppInfo/
      appinfo.ini
      appicon.ico
      appicon_16.png
      appicon_32.png
  Data/
    Profile/                             Preferences, crawl SQLite, logs, browser downloads
      playwright-browsers/
    Session/                             Chromium cookies/cache/session state
    Crashes/                             Crash reports
    Logs/                                Electron's logs path
    Temp/                                Scoped TEMP and TMP for child processes
  Other/Source/                          Provenance, adapter code, MIT license texts
  PortableApps-README.txt
```

The source adapter in `scripts/builder.py` patches `apps/desktop/src/main/index.ts` before `app.requestSingleInstanceLock()` and before Electron readiness. It redirects Electron `userData`, `sessionData`, `crashDumps` and log paths. FreeCrawl's existing Playwright setup stores its downloaded Chromium under `app.getPath('userData')/playwright-browsers`; the launcher sets the matching `PLAYWRIGHT_BROWSERS_PATH` early. The launcher sets **TEMP/TMP only in its own process and spawned children**, not system-wide.

This is NOT a post-exit AppData scavenger. `TraceGuard` and `ShellGuard` were intentionally **not** implemented because current inspected source did not establish specific, safely attributable runtime host paths or shell registrations requiring destructive recovery. If a real Windows trace exposes additional application-owned locations, add *narrow* protection only after checking pre-existing host data; never broadly delete AppData/LocalAppData/ProgramData or shortcuts.

## Release naming and provenance

The workflow resolves stable release tags with numeric semantic-version sorting, verifies GitHub's tag-to-commit object, fetches only the matching ref, and fails if the checked-out full SHA differs. It records the SHA-256 of the upstream `package-lock.json`, upstream license, builder version and package revision. The standard ZIP name resembles:

`FreeCrawlSEOToolPortable-<stable-tag>-<package-revision>-<eight-digit-commit-prefix>.zip` (actual name and checksum are calculated during CI).

The installer filename is obtained from the **actual shared Package Builder output**, never guessed. The release tag is `portable-freecrawl-<upstreamTag>-<packageRevision>-<shortCommit>`. If that exact release already exists, the workflow skips building/publishing; change package revision for intentional changes. No automatic pruning. Publisher dry-run must succeed before live publication.

The shared actions are pinned to **verified full release commits**, not floating tags: Package Builder `v1.0.0` → `0112c35580e83b37eb8757ebcb949274e1631a04`; Release Publisher `v1.1.1` → `cb64f86ac2d8c67506db5832de07f9ff58cbeaeb`. The preflight reads each actual pinned `action.yml`, inspects its interface, and fails if required fields disappear.

## Safety and limits

- Source code is MIT-licensed, but third-party dependencies retain their own license obligations. Keep the Electron `LICENSE.electron.txt` and `LICENSES.chromium.html` bundled by electron-builder. Brand artwork is taken only from upstream source assets.
- No elevation, drivers, services, automatic startup entry, machine registry editing, file association registration, or permanent environment-variable changes are requested by the launcher. The upstream Electron app may still create **Windows-managed notification, GPU, search, recent-file or crash state**; these are not automatically deleted.
- FreeCrawl's own **Help → Check for Updates** can download an upstream SETUP installer to Downloads. Do **not** run it over this portable package; update through this builder. Normal exports and saved project locations explicitly chosen in Documents, Downloads, or another directory are not silently moved into Data.
- The MCP bridge discovery file, logs, working SQLite files, JSON preferences, and the app's Playwright Chromium cache derive from the portable user-data directory. External OAuth/browser-based integrations, encryption tied to Windows user credentials, and third-party tools may need reauthorization after relocation.
- The app stores absolute recent-project paths. Moving drives or folders may leave old recent entries; open your saved projects from the new location. Move the full portable folder, not just the EXE.
- The workflow builds unattended, but GUI, notification click-through, installed-app coexistence, file associations, injected browser tests, crash/kill recovery and real installer upgrade tests require a **real interactive Windows session**. See `docs/WINDOWS-ACCEPTANCE.md` and `docs/VALIDATION-AND-SECURITY.md`.
- No code signing or antivirus immunity is claimed. Very large Playwright browser downloads may consume USB space. The first JS-render crawl may require a network connection.
- Avoid running the internal app executable directly: the root launcher supplies the required environment for portable storage.

## Troubleshooting

| Error | Practical fix |
| --- | --- |
| `Stable published release ... not found` | Use `latest` or an actual upstream stable release version. Never build unverified `main`. |
| `Source tag moved or mismatched` | Stop. Do not bypass the check; review upstream release identity. |
| `Upstream initialization anchor changed` | The newer upstream source no longer matches the audited adapter location; update and review the patch before releasing. |
| `npm ci` or TypeScript errors | Inspect that job's npm/build logs and ensure the upstream release itself builds on Node 22. Do not discard the lockfile. |
| Electron ZIP executable missing | Confirm electron-builder placed `win-unpacked` under `apps/desktop/release` and the process ended without errors. |
| MSVC or CMake fails | Review `vswhere` toolchain output. The workflow supports verified VS 2022/2026 hosted toolchains. |
| `.paf.exe` generation fails | The workflow keeps the validated ZIP in Actions artifacts if generated; inspect shared Package Builder logs, and do not mark installer as successful. |
| Portable preferences disappear after restart | Check root EXE, Data/Profile permissions, storage redirection patch, and anti-malware file locks. Do not blindly move or delete host AppData. |
| JavaScript-render feature needs Chromium | From inside FreeCrawl, allow browser download, then verify `Data/Profile/playwright-browsers`. |
| PortableApps menu does not show the app | Refresh the Platform menu and confirm root EXE and `App/AppInfo/appinfo.ini`. |
| Rebuild has no new Release | An identical release tag intentionally skips to prevent duplicate overwrites. Bump `package_revision`. |

**Status of this kit:** Offline builder-unit tests and workflow static checks can be executed without Windows. Compilation, live app behavior, ZIP/PAF generation, and release publication must still be proven on GitHub's Windows runner and an interactive Windows PC. No successful run is claimed in this README.
