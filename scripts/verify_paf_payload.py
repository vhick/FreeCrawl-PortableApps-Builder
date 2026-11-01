"""Validate the actual PAF/NSIS payload without running a GUI installer.

The official PA.c installer can require PortableApps.com Platform for unattended
installation. Generic NSIS /S /D flags do not guarantee the wizard will close.
This is a real archive test, NOT an install/upgrade behavior test.
"""
from __future__ import annotations

import argparse
import configparser
import os
import re
import shutil
import subprocess
from pathlib import Path

REQUIRED = (
    'freecrawlportable.exe',
    'appinfo.ini',
    'installer.ini',
    'freecrawl seo tool.exe',
    'app.asar',
)


def find_7z() -> str:
    for possible in (r'C:\Program Files\7-Zip\7z.exe',
                     r'C:\Program Files (x86)\7-Zip\7z.exe'):
        if Path(possible).is_file():
            return possible
    found = shutil.which('7z') or shutil.which('7za')
    if not found:
        raise RuntimeError('7-Zip not found. The Windows runner requires 7z.exe.')
    return found


def run(args: list[str], timeout: int):
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                                errors='replace', timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f'7-Zip exceeded {timeout}s while checking the PAF archive') from exc
    if result.returncode != 0:
        raise RuntimeError(f'7-Zip failed with exit {result.returncode}: '
                           f'{(result.stdout + result.stderr)[-2500:]}')
    return result.stdout


def verify_manifest(listing: str) -> None:
    # 7-Zip's -slt reports real NSIS payload paths; do not treat strings in PE
    # metadata as proof that a file was packaged.
    paths = [line[7:].strip().replace('\\', '/').casefold()
             for line in listing.splitlines() if line.startswith('Path = ')]
    # The first Path may be the archive itself, so matching must be anchored to
    # filename boundaries, not substring matches (which could give false positives).
    if len(paths) < 10:
        raise RuntimeError(f'Unexpectedly short NSIS archive listing: {len(paths)} paths')
    for filename in REQUIRED:
        if not any(path == filename or path.endswith('/' + filename) for path in paths):
            raise RuntimeError('PAF payload is missing ' + filename +
                               '; example files: ' + ', '.join(paths[:18]))
    print(f'PASS: official/fallback PAF archive lists {len(paths)} records including all application payload files')


def verify_staged_policy(stage: Path) -> None:
    ini=stage / 'App' / 'AppInfo' / 'installer.ini'
    info=stage / 'App' / 'AppInfo' / 'appinfo.ini'
    if not info.is_file() or not ini.is_file():
        raise RuntimeError('Required PortableApps metadata is missing from staging')
    cfg=configparser.ConfigParser(interpolation=None)
    cfg.read(ini, encoding='utf-8')
    if cfg.get('MainDirectories', 'RemoveDataDirectory', fallback='').casefold()!='false':
        raise RuntimeError('Missing explicit RemoveDataDirectory=false in installer.ini')
    if cfg.get('MainDirectories','RemoveAppDirectory',fallback='').casefold()!='true':
        raise RuntimeError('Unexpected App upgrade policy')
    appcfg=configparser.ConfigParser(interpolation=None)
    appcfg.read(info, encoding='utf-8')
    if appcfg.get('Control','Start')!='FreeCrawlPortable.exe':
        raise RuntimeError('PortableApps entry executable is incorrect')
    data=stage/'Data'
    if not data.is_dir() or any(data.iterdir()):
        raise RuntimeError('Release staging must contain an empty Data directory')
    print('PASS: staged appinfo.ini, installer.ini (explicit preserve Data), and empty Data directory')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('paf')
    parser.add_argument('--stage',required=True)
    args=parser.parse_args()
    package=Path(args.paf).resolve()
    if not package.is_file() or package.stat().st_size<150_000:
        raise RuntimeError('PAF missing or too small')
    with package.open('rb') as f:
        if f.read(2)!=b'MZ':
            raise RuntimeError('PAF lacks Windows MZ signature')
        f.seek(0x3c)
        offset=int.from_bytes(f.read(4),'little')
        if offset<64 or offset>1024*1024:
            raise RuntimeError('PAF lacks valid PE header offset')
        f.seek(offset)
        if f.read(4)!=b'PE\0\0':
            raise RuntimeError('PAF lacks PE signature')
    verify_staged_policy(Path(args.stage))
    exe=find_7z()
    listing=run([exe, 'l', '-slt', str(package)],timeout=90)
    verify_manifest(listing)
    print('Testing complete NSIS compressed payload (no GUI install)...')
    result=run([exe,'t','-y','-bd',str(package)],timeout=240)
    if 'Everything is Ok' not in result:
        raise RuntimeError('7-Zip did not confirm NSIS payload integrity')
    print(f'PASS: real PAF passed complete archive decompression test ({package.stat().st_size:,} bytes)')
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a',encoding='utf-8') as output:
            output.write('## FreeCrawl installer checks\n\n'
                '- Official PortableApps.com Installer is used when the build reported `official`.\n'
                '- PAF PE header, embedded required file list, and full compressed payload: **PASS**.\n'
                '- `installer.ini` explicitly retains existing `Data`: **PASS (configuration only)**.\n'
                '- PAF interactive installation and real upgrade preserving Data: **NOT TESTED on runner**.\n'
                '- Install the PAF manually through PortableApps Menu and verify Data retention before using it for production updates.\n')
    print('LIMITATION: Interactive PAF installation and an actual upgrade were NOT tested. '
          'Manual PortableApps Menu installation/upgrade test is still required.')


if __name__ == '__main__':
    main()
