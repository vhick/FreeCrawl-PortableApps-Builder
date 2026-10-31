# FreeCrawl SEO Tool — PortableApps Builder r2 (ZIP + genuine PAF)

**PORTABLEAPPS mode.** This independent builder compiles FreeCrawl from the original stable release and produces BOTH a ready-to-extract PortableApps ZIP **and** a genuine `.paf.exe` built using the official PortableApps.com Installer. It builds one copy of Electron and one genuine native Windows x64 launcher, shared by both packages.

* Upstream application: https://github.com/kemalai/FreeCrawl-SEO-Tool (MIT license, original publisher Kemal Acar)
* Shared publisher: https://github.com/vhick/portable-release-publisher (your existing publisher action; **new PAF-supporting ref required**)
* Official packaging tool: PortableApps.com Installer 3.9.22, https://sourceforge.net/projects/portableapps/files/PortableApps.com%20Installer/PortableApps.comInstaller_3.9.22.paf.exe/download
* PortableApps.com Format: https://portableapps.com/development/portableapps.com_format (3.9)

This is **unofficial packaging**, not a PortableApps.com-certified app, and the resulting binaries are unsigned.

## VERY IMPORTANT — update your shared publisher BEFORE running r2

As checked on October 31, 2026, the **publicly accessible** `vhick/portable-release-publisher` repository's `main` and its `v1.0.1` tag still contain ZIP-only checks. These will reject the new `.paf.exe`. Your local changes may not yet be pushed. Do not replace/move the old `v1.0.1` tag; existing builders rely on it.

1. In GitHub Desktop, open your `portable-release-publisher` repository and **Commit** and **Push** the revised code that handles both `.zip` and `.paf.exe`.
2. Recommended: on GitHub, create **a new tag** for that tested publisher code, e.g. `v1.0.2` (or the actual version you've chosen). Do NOT recreate `v1.0.1`.
3. On the new FreeCrawl workflow's **Run workflow** page, set `publisher_ref` to that **new tag**. For an initial trial, `main` is the default and will work **only after** your updates have reached GitHub.
4. The workflow checks that the chosen publisher's action contract exists and its code mentions PAF support. It then tests both actual files through the **publisher's own dry-run** before using the **same action** to publish them. If your publisher isn't compatible, the workflow fails and publishes nothing. Neither this builder nor its scripts create a second release-publishing system.

**The new publisher must:** accept newline-separated `files` input; accept a genuine `.paf.exe` alongside `.zip`; validate/checksum the files; use the caller repository; preserve existing releases and drafts; publish `SHA256SUMS.txt`; honor `dry-run`, `prune`, `tag`, `tag-prefix` and `keep-releases` inputs. The shared publisher controls release retention, immutable releases and collision handling.

## Files produced by a successful Windows workflow

Example if upstream stable is v1.1.1:

- `FreeCrawlPortable_v1.1.1_r2_win64.zip`
- `FreeCrawlPortable_v1.1.1_r2_win64.paf.exe`
- `SHA256SUMS.txt` (written by the shared publisher, covering BOTH files)

GitHub release tag: `portable-freecrawl-v1.1.1-r2` (app version auto-resolved; revision is this builder's r2, NOT the publisher's release version).

Each contains a Windows `FreeCrawlPortable.exe` **compiled from ordinary C++**, a complete unpacked Electron app, valid PortableApps metadata, the upstream icon, and preserved license information. The app directory is:

```
FreeCrawlPortable/
  FreeCrawlPortable.exe
  App/
    AppInfo/
      appinfo.ini
      installer.ini
      appicon.ico
      appicon_16.png, appicon_32.png, appicon_75.png, ...
      Launcher/README.txt
    FreeCrawl/FreeCrawl SEO Tool.exe  (+ application files)
    DefaultData/
  Data/                         <- ALL persistent app profile data lives here
  Other/Source/                 <- upstream MIT license + launcher/patch source
  help.html
```

The official `.paf.exe` installs and updates this layout. `App/AppInfo/installer.ini` asks the official installer to replace old `App` and `Other` directories, check for running FreeCrawl, and preserve existing `Data` (no `RemoveDataDirectory` setting).

## GitHub Desktop instructions — fresh independent repository

1. Download and extract this ZIP **builder kit** on Windows. Make sure you see `.github`, `scripts`, `launcher`, `docs`, and `README.md` in the extracted directory.
2. In GitHub Desktop, choose **File → New repository**, name it `FreeCrawl-PortableApps-Builder`, and select your intended local folder. Click **Create repository**.
3. Open that repository's local folder from GitHub Desktop. Copy the **contents** of the extracted builder ZIP into the repository folder. Do not place the entire extracted folder as a subfolder; `.github/workflows/build-portableapps.yml` must be in the repository root hierarchy.
4. Return to GitHub Desktop. Enter summary `FreeCrawl PortableApps ZIP and PAF builder r2`, then **Commit to main**.
5. Click **Publish repository**. Choose **Private** if you want private GitHub Releases or **Public** if you want publicly accessible releases. The builder will never change that visibility.
6. On GitHub, go to your repository **Settings → Actions → General** and allow Actions/workflow runs. In **Workflow permissions**, allow read and write if required for release creation. The job explicitly declares `contents: write`.
7. Ensure your **shared publisher** has a pushed version that actually supports `.paf.exe` (see warning above). Prefer the new tag rather than the changing `main` branch.
8. Go to **Actions → Build FreeCrawl PortableApps ZIP and PAF Installer → Run workflow**. Enter your actual PAF-enabled `publisher_ref` (new tag or `main`, once updated).
9. After a **successful** workflow run, go to the builder repository's **Releases** and open the `portable-freecrawl-...-r2` entry. Download the `.paf.exe` (recommended) or the ZIP (manual extraction). Verify against `SHA256SUMS.txt` if desired.

### If you already created the r1 builder repository

You do **not** need a new repository. Download/extract this r2 kit, replace the r1 builder's workflow/scripts/README files, leave your existing `.git` folder alone, then **Commit to main → Push origin** using GitHub Desktop. This bumps package release tags to `r2`; old r1 releases are not overwritten.

## Install from the official-format `.paf.exe` (recommended)

1. In PortableApps Menu, select **Apps → Install a New App**.
2. Select the new `FreeCrawlPortable_v..._r2_win64.paf.exe` file.
3. Follow the installation prompts, selecting the existing PortableApps directory if necessary.
4. Refresh PortableApps Menu if it does not appear immediately.
5. Run **FreeCrawl SEO Tool Portable**. It starts `FreeCrawlPortable.exe` and stores settings and databases under `FreeCrawlPortable\Data\Profile`.

For updates, **fully exit FreeCrawl first**, back up the existing `Data` directory, and run the newer `.paf.exe` installer against the same PortableApps parent folder. The installer should leave `Data` intact; r2 also tests this automatically on a disposable Windows runner. The real user should back up important `.seoproject` SQLite databases as a precaution.

### Install from the ZIP

Extract the complete **`FreeCrawlPortable` folder** to `<Your PortableApps Folder>\FreeCrawlPortable`. Refresh PortableApps Menu. The launcher is the actual root-level `FreeCrawlPortable.exe` and is NOT a CMD script.

To upgrade an existing ZIP-based installation, keep its original `Data` directory, and replace `App`, `Other`, `FreeCrawlPortable.exe` and `help.html` with the new ZIP's contents. Do not simply delete the previous folder and extract a new one, as that would delete your projects and preferences.

## Genuine portability behavior

The builder patches the original Electron startup before the application's logging, app initialization, and single-instance lock. The native C++ launcher creates directories only under `Data` and sets environment variables for its child. Paths are relative to the portable directory and do not depend on a particular drive letter.

- Electron `userData` and SQLite `.seoproject` working databases: `Data\Profile`
- Chromium session/profile: `Data\Profile\Chromium`
- Playwright browser cache/downloads: `Data\Profile\playwright-browsers`
- Chromium disk cache: `Data\Cache`
- Application temporary files: `Data\Temp`
- No Windows service, driver, registry integration, autostart, scheduled task, admin request or AV exception is created by this builder.

**Limits:** Windows itself can maintain traces (recent files, prefetch, OS caches, crash-reporting), and users can manually export reports to Documents or other locations. External auth tokens may be Windows-account bound. These are not deleted or silently migrated. The `.paf.exe` does not eliminate OS-generated traces.

## Validation and quality gates

The GitHub workflow fails rather than releasing a missing or invalid file.

1. Resolve the latest stable semver release, skipping prereleases.
2. Confirm the shared publisher supports PAF; use a ref selected at runtime.
3. Build FreeCrawl using `npm ci`, `npm run build` and electron-builder unpacked output.
4. Build a real x64 PortableApps launcher with MSVC/CMake and upstream icon.
5. Generate valid Format 3.9 metadata and a ZIP; validate its PE binaries, icons, content and empty Data folder.
6. Download the **unmodified** official PortableApps.com Installer v3.9.22 with SHA-256 `689456f1fb1320c45e82a077afe6b87fb388fd3f75c41d9ee9ce8d45f3966b67`, checked against SourceForge's published checksum (as of 2026-10-31). Install this tool only in a disposable runner directory.
7. Pass `stage\FreeCrawlPortable` directly to the official installer executable to create the *actual* `.paf.exe`, not a renamed ZIP.
8. Verify the output's executable header, then **install it silently in an isolated test directory**, verify required portable files, write `Data\keep-existing-data.txt`, reinstall to simulate an upgrade, and confirm that file remains unchanged.
9. Start FreeCrawl through the compiled launcher in a different throwaway ZIP extraction, then relocate the complete folder and confirm the stored profile remains intact.
10. Invoke your existing shared publisher for **both packages** with `dry-run=true`. Publish both files using the same publisher action only after passing every check.

**Not locally verified:** This kit has not been compiled on a Windows GitHub-hosted runner in this chat. The test steps are included, but they must actually pass on GitHub before claiming working final `.paf.exe` or PortableApps Menu discovery. PortableApps Menu discovery and real hardware behavior should also be tested on your own PC.

## Publishing, GitHub Free, security

- Only manual GitHub Actions triggers; no scheduled builds or automatic Actions artifact uploads.
- Same hosted Windows job compiles, packages, tests, and uses the shared publisher to transfer files **directly into the caller's GitHub Releases**.
- Public builder → public release; private builder → private release. No other repository is targeted; no separate PAT is needed.
- Duplicate release tags are safely skipped only when the matching ZIP, PAF, and checksum asset names already exist with the recognized publisher marker. Conflicts/drafts fail closed.
- Release pruning is deliberately **off** (`prune: false`). `keep-releases: 3` remains set for future opt-in retention.
- No encoded scripts, obfuscated script wrappers, unnecessary elevated privileges, antivirus disablement, or code-signing impersonation. The Windows binaries will be unsigned unless legitimate signing is configured separately.
- The official PortableApps.com Installer is licensed for the relevant free/open-source packaging usage. The upstream MIT license is included in the package. Trademarks, unrelated third-party dependencies, and redistribution requirements still apply; this is not endorsed by the upstream author or PortableApps.com.
- A release asset must remain below GitHub's per-file size limit, and private Actions minutes still count. A failed build can use compute time even without Actions artifact uploads.

## Troubleshooting

**`Selected publisher is not PAF-capable`:** The publicly accessible ref is still ZIP-only. Push your updates to `vhick/portable-release-publisher`, create a new immutable tag, and rerun the workflow choosing that tag. **Do not retag v1.0.1.**

**`Cannot download official PortableApps.com Installer` or `SHA mismatch`:** SourceForge mirror may be temporarily unavailable, or official stable version may have changed. Verify the latest approved stable download and its SHA-256 on SourceForge before updating both values in `scripts/build_installer.ps1`. Never disable the hash check.

**`Expected one ... installer.exe` or `.paf.exe` output not found`:** PortableApps.com's tool changed its extraction structure or detected invalid app metadata. Examine the `Build authentic PAF` step and its installer log, if present. Do not substitute a ZIP renamed `.paf.exe`.

**`PAF install verification failed`:** Inspect the disposable test installation layout and install arguments. The publisher will not run unless the test passes, protecting your release feed from untested installers.

**`Upstream compilation/patch failed`:** A newer FreeCrawl release may have changed source files, build layout, icons, or filenames. The script refuses to guess; examine the failed build and update guarded patches in a later builder revision.

**`FreeCrawlPortable.exe` not visible in PortableApps Menu:** Make sure it is at `PortableApps\FreeCrawlPortable\FreeCrawlPortable.exe` and `App\AppInfo\appinfo.ini` has `Start=FreeCrawlPortable.exe`, then refresh the menu. The builder automatically checks the launcher/header/layout but cannot remotely verify your menu installation.

**FreeCrawl browser feature wants a download:** The workflow skips auto-downloading Playwright browser during build; it goes into the portable profile when first needed. Keep enough drive space and network connectivity.

**Workflow succeeds but the app is unsigned:** That is expected for a personal builder. Do not disable antivirus; keep hash verification and review unexpected warnings.

## Auditing references

See `docs/SOURCE-AUDIT.md` for the upstream storage audit and documented portability limitations, and `launcher/FreeCrawlPortable.cpp` for the real native executable's source.
