#!/usr/bin/env python3
"""Build controller for source-built FreeCrawl SEO Tool PortableApps (Windows CI).
This script does NOT download or execute unverified application binaries.
"""
from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile

UPSTREAM = 'kemalai/FreeCrawl-SEO-Tool'
ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'work'
SOURCE = WORK / 'upstream'
STAGED = WORK / 'stage' / 'FreeCrawlSEOToolPortable'
DIST = ROOT / 'dist'
REVISION = 'b1r1'  # This kit revision; users may provide a package revision separately.


def request_json(url: str, allow404: bool = False):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'FreeCrawl-PortableApps-Builder-b1r1',
               'X-GitHub-Api-Version': '2022-11-28'}
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and allow404:
            return None
        raise RuntimeError(f'GitHub API HTTP {exc.code} for {url} (do not treat as empty releases)') from exc


def write_output(data):
    path = os.environ.get('GITHUB_OUTPUT')
    if path:
        with open(path, 'a', encoding='utf-8', newline='\n') as stream:
            for key, value in data.items():
                stream.write(f'{key}={value}\n')


def semver(tag: str):
    m = re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?', tag)
    return tuple(int(x) for x in m.groups(default='0')) if m else None


def resolve(version: str, package_revision: str, publishing: bool):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,24}', package_revision):
        raise ValueError('Invalid package revision; use letters/digits/dot/hyphen only')
    candidates = []
    # GitHub pagination: don't let an older/newer prerelease mask stable releases.
    for page in range(1, 5):
        batch = request_json(f'https://api.github.com/repos/{UPSTREAM}/releases?per_page=100&page={page}')
        if not isinstance(batch, list):
            raise RuntimeError('Unexpected GitHub releases response')
        for release in batch:
            tag = release.get('tag_name', '')
            parsed = semver(tag)
            if parsed and not release.get('draft') and not release.get('prerelease'):
                candidates.append((parsed, release))
        if len(batch) < 100:
            break
    if not candidates:
        raise RuntimeError('No suitable published stable semver release')
    if version == 'latest':
        _sort, selected = max(candidates, key=lambda row: row[0])
    else:
        matching = [r for _, r in candidates if r['tag_name'].lstrip('v') == version.lstrip('v')]
        if not matching:
            raise RuntimeError(f'Stable published release {version!r} not found')
        selected = matching[0]
    tag = selected['tag_name']
    obj = request_json(f'https://api.github.com/repos/{UPSTREAM}/git/ref/tags/{tag}')
    target = obj['object']
    if target['type'] == 'tag':
        target = request_json(target['url'])['object']
    if target['type'] != 'commit' or not re.fullmatch('[0-9a-f]{40}', target['sha']):
        raise RuntimeError('Could not resolve release tag to a real 40-digit commit')
    sha = target['sha']
    reltag = f'portable-freecrawl-{tag}-{package_revision}-{sha[:8]}'
    name = f'FreeCrawlSEOToolPortable-{tag}-{package_revision}-{sha[:8]}.zip'
    skip = False
    if publishing:
        repo = os.environ.get('GITHUB_REPOSITORY')
        if not repo:
            raise RuntimeError('GITHUB_REPOSITORY missing; cannot safely test release identity')
        existing = request_json(f'https://api.github.com/repos/{repo}/releases/tags/{reltag}', allow404=True)
        if existing is not None:
            if existing.get('tag_name') != reltag:
                raise RuntimeError('Existing release identity mismatch')
            if existing.get('draft') or '<!-- portable-release-publisher:managed:v2 -->' not in (existing.get('body') or ''):
                raise RuntimeError('Tag belongs to a draft/unrelated release; refusing to confuse it with this build')
            actual_assets = {a.get('name') for a in existing.get('assets', [])}
            if name not in actual_assets or 'SHA256SUMS.txt' not in actual_assets or not any(
                a.endswith('.paf.exe') for a in actual_assets if isinstance(a, str)):
                raise RuntimeError('Existing managed release lacks expected ZIP/PAF/checksum; inspect, do not silently skip')
            skip = True
            print(f'Existing complete managed release {reltag}; refusing rebuild/overwrite. Bump package_revision for new package.')
    WORK.mkdir(parents=True, exist_ok=True)
    identity = {'tag': tag, 'version': tag.lstrip('v'), 'commit': sha,
                'package_revision': package_revision, 'builder_revision': REVISION,
                'release_tag': reltag, 'zip_name': name, 'source_repo': UPSTREAM}
    (WORK / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8')
    write_output({'version': identity['version'], 'tag': tag, 'sha': sha, 'release_tag': reltag,
                  'zip_name': name, 'skip': str(skip).lower()})
    print(json.dumps(identity, indent=2))


def run(*args, cwd=None):
    print('+', ' '.join(str(x) for x in args), flush=True)
    subprocess.run([str(x) for x in args], cwd=cwd, check=True)


def fetch():
    identity = json.loads((WORK / 'identity.json').read_text(encoding='utf-8'))
    if SOURCE.exists():
        raise RuntimeError('Refusing to overwrite work/upstream; fresh CI clone required')
    SOURCE.mkdir(parents=True)
    run('git', 'init', '-q', str(SOURCE))
    run('git', 'remote', 'add', 'upstream', f'https://github.com/{UPSTREAM}.git', cwd=SOURCE)
    run('git', '-c', 'protocol.version=2', 'fetch', '--depth=1', 'upstream', f'refs/tags/{identity["tag"]}', cwd=SOURCE)
    run('git', 'checkout', '--detach', '--quiet', 'FETCH_HEAD', cwd=SOURCE)
    found = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip()
    if found != identity['commit']:
        raise RuntimeError(f'Source tag moved or mismatched: expected {identity["commit"]}, got {found}')
    lock = SOURCE / 'package-lock.json'
    if not lock.is_file():
        raise RuntimeError('Upstream package-lock.json is missing')
    package = json.loads((SOURCE / 'package.json').read_text(encoding='utf-8'))
    desktop = json.loads((SOURCE / 'apps/desktop/package.json').read_text(encoding='utf-8'))
    if package.get('version') != identity['version'] or desktop.get('version') != identity['version']:
        raise RuntimeError('Upstream package.json does not match resolved stable release')
    if package.get('license') != 'MIT' or not (SOURCE / 'LICENSE').is_file():
        raise RuntimeError('Unexpected upstream license; requires review')
    identity['lock_sha256'] = sha256(lock)
    (WORK / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8')
    print(f'Verified commit {found}; lockfile SHA256 {identity["lock_sha256"]}')


def patch():
    index = SOURCE / 'apps/desktop/src/main/index.ts'
    original = index.read_text(encoding='utf-8')
    marker = '// Single-instance guard. Without this'
    if original.count(marker) != 1:
        raise RuntimeError('Upstream initialization anchor changed; stop and audit source')
    if 'FREECRAWL_PORTABLE_DATA' in original:
        raise RuntimeError('Upstream already contains a portable-data patch; audit for duplication')
    adapter = '''// FREECRAWL_PORTABLEAPPS_b1r1: early, source-level storage isolation.\n// Root launcher supplies an absolute Data path. Normal upstream builds are unchanged.\nconst freecrawlPortableDataRoot = process.env.FREECRAWL_PORTABLE_DATA;\nif (freecrawlPortableDataRoot) {\n  if (!isAbsolute(freecrawlPortableDataRoot)) {\n    throw new Error('FREECRAWL_PORTABLE_DATA must be absolute');\n  }\n  const portableBase = resolvePath(freecrawlPortableDataRoot);\n  for (const folder of ['Profile', 'Session', 'Crashes', 'Logs', 'Temp']) {\n    mkdirSync(join(portableBase, folder), { recursive: true });\n  }\n  app.setPath('userData', join(portableBase, 'Profile'));\n  app.setPath('sessionData', join(portableBase, 'Session'));\n  app.setPath('crashDumps', join(portableBase, 'Crashes'));\n  app.setAppLogsPath(join(portableBase, 'Logs'));\n}\n\n'''
    index.write_text(original.replace(marker, adapter + marker, 1), encoding='utf-8', newline='\n')
    text = index.read_text(encoding='utf-8')
    required = ['app.setPath(\'userData\'', 'app.setPath(\'sessionData\'', 'app.setAppLogsPath(',
                'app.setPath(\'crashDumps\'', 'FREECRAWL_PORTABLEAPPS_b1r1']
    if not all(s in text for s in required) or text.index('FREECRAWL_PORTABLEAPPS_b1r1') > text.index('app.requestSingleInstanceLock()'):
        raise RuntimeError('Portable adapter placement validation failed')
    print('Applied early Electron path adapter; stock normal launch remains unchanged.')



def verify_compiled_adapter():
    """Ensure actual electron-vite output contains the source adapter, not only a patched input."""
    output = SOURCE / 'apps/desktop/out/main'
    if not output.is_dir():
        raise RuntimeError('Missing actual built Electron main JavaScript directory')
    files = list(output.rglob('*.js'))
    if not files:
        raise RuntimeError('No compiled Electron main JavaScript found')
    contents = '\n'.join(x.read_text(encoding='utf-8', errors='replace') for x in files)
    if 'FREECRAWL_PORTABLE_DATA' not in contents or 'sessionData' not in contents or 'crashDumps' not in contents:
        raise RuntimeError('Compiled Electron code does not contain required portable paths')
    print(f'COMPILED SOURCE ADAPTER VERIFIED in {len(files)} built Electron main JS files')


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fp:
        for block in iter(lambda: fp.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def assert_pe(path: Path, architecture: int | tuple[int, ...] = 0x8664):
    if not path.is_file() or path.stat().st_size < 10240:
        raise ValueError(f'PE executable missing or implausibly small: {path}')
    with path.open('rb') as fp:
        if fp.read(2) != b'MZ':
            raise ValueError(f'Missing MZ signature: {path}')
        fp.seek(0x3C)
        offset = struct.unpack('<I', fp.read(4))[0]
        if offset > 16 * 1024 * 1024:
            raise ValueError('Invalid PE header offset')
        fp.seek(offset)
        if fp.read(4) != b'PE\x00\x00':
            raise ValueError(f'Missing PE signature: {path}')
        machine = struct.unpack('<H', fp.read(2))[0]
        allowed = (architecture,) if isinstance(architecture, int) else architecture
        if machine not in allowed:
            raise ValueError(f'Wrong PE machine {machine:#x}; expected {allowed!r} for {path}')


def stage():
    identity = json.loads((WORK / 'identity.json').read_text(encoding='utf-8'))
    unpacked = SOURCE / 'apps/desktop/release/win-unpacked'
    exe = unpacked / 'FreeCrawl SEO Tool.exe'
    assert_pe(exe)
    if not (unpacked / 'resources/app.asar').is_file():
        raise RuntimeError('electron-builder win-unpacked missing resources/app.asar')
    if STAGED.exists():
        raise RuntimeError('Destination already exists; refusing accidental in-place upgrade')
    shutil.copytree(unpacked, STAGED / 'App/FreeCrawl')
    appinfo = STAGED / 'App/AppInfo'
    appinfo.mkdir(parents=True)
    launcher = WORK / 'launcher-build/Release/FreeCrawlSEOToolPortable.exe'
    assert_pe(launcher)
    shutil.copy2(launcher, STAGED / 'FreeCrawlSEOToolPortable.exe')
    icon = SOURCE / 'apps/desktop/resources/icon.ico'
    if not icon.is_file() or icon.stat().st_size < 128:
        raise RuntimeError('Original upstream icon.ico is missing; do not substitute unlicensed artwork')
    shutil.copy2(icon, appinfo / 'appicon.ico')
    for size in (16, 32):
        image = WORK / f'icon_{size}.png'
        if not image.is_file() or not image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
            raise RuntimeError(f'Missing real PNG generated from upstream icon: {image}')
        shutil.copy2(image, appinfo / f'appicon_{size}.png')
    version = identity['version'].split('.')
    package_version = '.'.join((version + ['0'] * 4)[:4])
    ini = f'''[Format]\nType=PortableApps.comFormat\nVersion=3.8\n\n[Details]\nName=FreeCrawl SEO Tool Portable (Community)\nAppId=FreeCrawlSEOToolPortableCommunity\nPublisher=Kemal Acar and Community Contributors\nHomepage=https://github.com/kemalai/FreeCrawl-SEO-Tool\nCategory=Utilities\nDescription=Source-built portable FreeCrawl SEO desktop audit application\nLanguage=Multilingual\n\n[License]\nShareable=true\nOpenSource=true\nFreeware=true\nCommercialUse=true\n\n[Version]\nPackageVersion={package_version}\nDisplayVersion={identity['version']} ({identity['package_revision']})\n\n[Control]\nIcons=1\nStart=FreeCrawlSEOToolPortable.exe\n'''
    (appinfo / 'appinfo.ini').write_text(ini, encoding='utf-8', newline='\n')
    for folder in ['Data/Profile/playwright-browsers', 'Data/Session', 'Data/Crashes', 'Data/Logs', 'Data/Temp']:
        (STAGED / folder).mkdir(parents=True, exist_ok=True)
    source_out = STAGED / 'Other/Source'
    source_out.mkdir(parents=True)
    shutil.copy2(SOURCE / 'LICENSE', source_out / 'FreeCrawl-LICENSE.txt')
    shutil.copy2(ROOT / 'LICENSE', source_out / 'Portable-Builder-LICENSE.txt')
    shutil.copy2(ROOT / 'scripts/builder.py', source_out / 'portable-adapter-source.py')
    (source_out / 'BUILD-IDENTITY.json').write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8')
    (STAGED / 'Other/Source/README.txt').write_text(
        'Source: https://github.com/kemalai/FreeCrawl-SEO-Tool\n'
        f'Tag: {identity["tag"]}\nCommit: {identity["commit"]}\n'
        f'Lockfile SHA256: {identity["lock_sha256"]}\n'
        'Minimal source adapter: scripts/builder.py patch() before Electron initialization.\n', encoding='utf-8')
    (STAGED / 'PortableApps-README.txt').write_text(
        'Launch FreeCrawlSEOToolPortable.exe from the folder root.\n'
        'Portable data: Data\\Profile; Chromium session: Data\\Session.\n'
        'First JS-render crawl can download Chromium to Data\\Profile\\playwright-browsers.\n'
        'Do not delete Data during upgrades. Exports to user-selected Documents/Downloads remain external.\n'
        'Help > Check for Updates may download an upstream SETUP installer; install only via this builder.\n'
        'This is an independent community package, not PortableApps.com-certified.\n', encoding='utf-8')
    validate_stage(STAGED)
    DIST.mkdir(parents=True, exist_ok=True)
    archive = DIST / identity['zip_name']
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for folder, dirs, files in os.walk(STAGED):
            relative_dir = Path(folder).relative_to(STAGED.parent).as_posix()
            z.writestr(relative_dir + '/', '')
            for filename in sorted(files):
                filepath = Path(folder) / filename
                z.write(filepath, (Path(relative_dir) / filename).as_posix())
    validate_zip(archive)
    (WORK / 'zip-sha256.txt').write_text(f'{sha256(archive)}  {archive.name}\n', encoding='utf-8')
    print(f'Validated ZIP: {archive} sha256={sha256(archive)}')


def validate_stage(stage_path: Path):
    if stage_path.name != 'FreeCrawlSEOToolPortable':
        raise RuntimeError('Incorrect PortableApps root name')
    assert_pe(stage_path / 'FreeCrawlSEOToolPortable.exe')
    assert_pe(stage_path / 'App/FreeCrawl/FreeCrawl SEO Tool.exe')
    if not (stage_path / 'App/FreeCrawl/resources/app.asar').is_file():
        raise RuntimeError('Application app.asar is missing')
    info = configparser.ConfigParser(interpolation=None)
    info.read(stage_path / 'App/AppInfo/appinfo.ini', encoding='utf-8')
    if info.get('Control', 'Start') != 'FreeCrawlSEOToolPortable.exe':
        raise RuntimeError('PortableApps start entry mismatch')
    if info.get('Format', 'Type') != 'PortableApps.comFormat':
        raise RuntimeError('Not a PortableApps format folder')
    if info.get('Details', 'AppId') != 'FreeCrawlSEOToolPortableCommunity':
        raise RuntimeError('Unexpected portable AppID')
    for path in ('App/AppInfo/appicon.ico', 'App/AppInfo/appicon_16.png', 'App/AppInfo/appicon_32.png',
                 'Data/Profile', 'Data/Temp', 'Other/Source/FreeCrawl-LICENSE.txt'):
        if not (stage_path / path).exists():
            raise RuntimeError(f'Required element missing: {path}')


def validate_zip(path: Path):
    if not path.is_file() or path.stat().st_size < 1_000_000:
        raise RuntimeError('Missing / implausibly small complete Electron ZIP')
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError(f'ZIP CRC failure: {bad}')
        names = set(z.namelist())
        base = 'FreeCrawlSEOToolPortable/'
        for name in (base+'FreeCrawlSEOToolPortable.exe', base+'App/FreeCrawl/resources/app.asar',
                     base+'App/AppInfo/appinfo.ini', base+'Data/', base+'Other/Source/FreeCrawl-LICENSE.txt'):
            if name not in names:
                raise RuntimeError(f'ZIP missing {name}')
        if any(name.startswith('/') or '..' in Path(name).parts for name in names):
            raise RuntimeError('ZIP path traversal entry found')
        if not z.read(base+'FreeCrawlSEOToolPortable.exe').startswith(b'MZ'):
            raise RuntimeError('ZIP launcher is not a PE')


def installer(path: str):
    item = Path(path).resolve()
    if item.suffix.lower() != '.exe' or not item.name.lower().endswith('.paf.exe'):
        raise RuntimeError('Installer path is not *.paf.exe')
    # NSIS installer bootstrap EXEs are commonly PE32/x86 even when payload is x64.
    # The actual application and root launcher MUST still be genuine x64 binaries.
    assert_pe(item, architecture=(0x014C, 0x8664))
    DIST.mkdir(parents=True, exist_ok=True)
    dest = DIST / item.name
    if dest != item:
        shutil.copy2(item, dest)
    print(f'Validated community NSIS installer PE: {dest.name}; SHA256 {sha256(dest)}')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='command', required=True)
    cmd = sub.add_parser('resolve')
    cmd.add_argument('--version', default='latest')
    cmd.add_argument('--package-revision', default=REVISION)
    cmd.add_argument('--publish', choices=('true', 'false'), default='true')
    sub.add_parser('fetch')
    sub.add_parser('patch')
    sub.add_parser('verify-compiled-adapter')
    sub.add_parser('stage')
    cmd = sub.add_parser('validate-installer')
    cmd.add_argument('--path', required=True)
    args = ap.parse_args()
    if args.command == 'resolve':
        resolve(args.version, args.package_revision, args.publish == 'true')
    elif args.command == 'fetch':
        fetch()
    elif args.command == 'patch':
        patch()
    elif args.command == 'verify-compiled-adapter':
        verify_compiled_adapter()
    elif args.command == 'stage':
        stage()
    elif args.command == 'validate-installer':
        installer(args.path)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'FAILED: {exc}', file=sys.stderr)
        raise
