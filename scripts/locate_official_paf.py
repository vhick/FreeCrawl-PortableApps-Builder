"""Safely identify an official build's output even if its generated name differs.

The vendor names the finished installer from app metadata; assuming a fixed prefix
can falsely report failure after a successful compression. All candidate files must
be new, outside the downloaded tool's own location, Windows PEs, and contain the
expected FreeCrawl launcher + metadata in their NSIS payload.
"""
from __future__ import annotations
import argparse, subprocess, sys, shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

def pe_signature(p: Path) -> bool:
    try:
        if p.stat().st_size < 150_000:
            return False
        with p.open('rb') as f:
            if f.read(2) != b'MZ': return False
            f.seek(0x3c)
            off=int.from_bytes(f.read(4),'little')
            if not (64 <= off < 1024 * 1024): return False
            f.seek(off)
            return f.read(4)==b'PE\0\0'
    except OSError:
        return False

def locate(roots: list[Path], started: datetime, seven_zip: Path):
    found=[]
    seen=set()
    for root in roots:
        if not root.is_dir(): continue
        for p in sorted(root.glob('*.paf.exe')):
            real=p.resolve()
            if real in seen: continue
            seen.add(real)
            if datetime.fromtimestamp(p.stat().st_mtime,timezone.utc)<started-timedelta(seconds=15):
                continue
            print(f'New PAF candidate: {p} ({p.stat().st_size:,} bytes)')
            if not pe_signature(p):
                print(f'SKIP: invalid Windows executable: {p}')
                continue
            try:
                listed=subprocess.run([str(seven_zip),'l','-slt',str(p)], text=True,
                        capture_output=True, timeout=90, check=False)
            except (OSError,subprocess.TimeoutExpired) as exc:
                print(f'SKIP: cannot inspect candidate: {exc}')
                continue
            manifest=(listed.stdout+listed.stderr).lower()
            if listed.returncode or 'freecrawlportable.exe' not in manifest or 'appinfo.ini' not in manifest:
                print(f'SKIP: NSIS payload does not contain FreeCrawl launch files: {p}')
                continue
            found.append(p)
    return found

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--started',required=True)
    ap.add_argument('--sevenzip',required=True)
    ap.add_argument('--target',required=True)
    ap.add_argument('--root',action='append',required=True)
    args=ap.parse_args()
    started=datetime.fromisoformat(args.started.replace('Z','+00:00')).astimezone(timezone.utc)
    roots=[Path(s) for s in args.root]
    matched=locate(roots, started, Path(args.sevenzip))
    if len(matched)>1:
        raise SystemExit('More than one verified FreeCrawl installer output; refusing ambiguous selection: '+str(matched))
    if not matched:
        print('OFFICIAL_PAF_NOT_FOUND: No newly generated, matching installer in documented output locations.')
        return 2
    target=Path(args.target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists(): raise SystemExit('Refusing to replace existing PAF: '+str(target))
    shutil.move(str(matched[0]),str(target))
    print('OFFICIAL_PAF_FOUND: '+str(target))
    return 0

if __name__=='__main__': sys.exit(main())
