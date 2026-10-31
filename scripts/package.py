"""Build a clean EXE-based PortableApps ZIP, never embedding user profiles or Actions artifacts."""
from __future__ import annotations
import argparse, json, shutil, zipfile
from pathlib import Path
from PIL import Image

APP_FOLDER='FreeCrawlPortable'
APP_EXE='FreeCrawl SEO Tool.exe'
LAUNCHER='FreeCrawlPortable.exe'
ICON_SIZES=(16,32,75,128,256)

def pe_x64(path:Path):
    with path.open('rb') as f:
        if f.read(2)!=b'MZ': raise RuntimeError(f'Not an MZ executable: {path}')
        f.seek(0x3c); offset=int.from_bytes(f.read(4),'little')
        if offset < 0x40 or offset > 0x100000: raise RuntimeError(f'Bad PE header: {path}')
        f.seek(offset)
        if f.read(4)!=b'PE\0\0' or int.from_bytes(f.read(2),'little')!=0x8664:
            raise RuntimeError(f'Not a 64-bit x86 Windows PE: {path}')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--upstream',default='upstream')
    p.add_argument('--unpacked',default='upstream/apps/desktop/release/win-unpacked')
    p.add_argument('--launcher',default='build/launcher/Release/FreeCrawlPortable.exe')
    p.add_argument('--output',default='dist')
    p.add_argument('--version',required=True)
    p.add_argument('--commit',required=True)
    p.add_argument('--revision',type=int,default=1)
    a=p.parse_args()
    upstream=Path(a.upstream)
    unpacked=Path(a.unpacked)
    launcher=Path(a.launcher)
    output=Path(a.output)
    if a.revision<=0: raise ValueError('Revision must be positive')
    source_version=json.loads((upstream/'package.json').read_text(encoding='utf-8'))['version']
    desktop_version=json.loads((upstream/'apps/desktop/package.json').read_text(encoding='utf-8'))['version']
    if source_version!=a.version or desktop_version!=a.version:
        raise RuntimeError(f'Upstream version mismatch: release={a.version}, root={source_version}, desktop={desktop_version}')
    if not unpacked.is_dir() or not (unpacked/APP_EXE).exists():
        raise RuntimeError('Expected electron-builder win-unpacked executable not found: '+str(unpacked/APP_EXE))
    pe_x64(unpacked/APP_EXE)
    pe_x64(launcher)
    stage=Path('stage')/APP_FOLDER
    if stage.parent.exists(): shutil.rmtree(stage.parent)
    app=stage/'App'/'FreeCrawl'
    app.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(unpacked,app)
    shutil.copy2(launcher,stage/LAUNCHER)
    appinfo=stage/'App'/'AppInfo'
    (appinfo/'Launcher').mkdir(parents=True)
    (stage/'App'/'DefaultData').mkdir()
    (stage/'Data').mkdir()
    notices=stage/'Other'/'Source'
    notices.mkdir(parents=True)
    icon=upstream/'apps/desktop/resources/icon.ico'
    icon_png=upstream/'apps/desktop/src/main/assets/window-icon.png'
    if not icon.is_file() or not icon_png.is_file():
        raise RuntimeError('Required upstream branded icons missing')
    shutil.copy2(icon,appinfo/'appicon.ico')
    shutil.copy2(upstream/'LICENSE',notices/'UPSTREAM-LICENSE.txt')
    # The upstream PNG is a true 256px artwork, not a 32px thumbnail enlarged to 256px.
    with Image.open(icon_png) as img:
        image=img.convert('RGBA')
        if image.width < 128 or image.height < 128:
            raise RuntimeError('Upstream source icon unexpectedly small')
        for n in ICON_SIZES:
            image.resize((n,n),Image.Resampling.LANCZOS).save(appinfo/f'appicon_{n}.png')
    major,minor,patch=map(int,a.version.split('.'))
    appinfo_ini=f'''[Format]
Type=PortableApps.comFormat
Version=3.9

[Details]
Name=FreeCrawl SEO Tool Portable
AppID=FreeCrawlPortable-vhick
BaseAppName=FreeCrawl SEO Tool
Publisher=Kemal Acar & vhick (independent portable packaging)
Homepage=https://github.com/kemalai/FreeCrawl-SEO-Tool
Category=Utilities
Description=Open source desktop website and SEO crawler
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true

[Version]
PackageVersion={major}.{minor}.{patch}.{a.revision}
DisplayVersion={a.version} Portable Revision {a.revision}

[Dependencies]
UsesJava=false
Requires64bitOS=true

[Control]
Icons=1
Start=FreeCrawlPortable.exe
'''
    (appinfo/'appinfo.ini').write_text(appinfo_ini,encoding='utf-8')
    # Official installer replaces App/Other but NEVER wipes Data during upgrades.
    (appinfo/'installer.ini').write_text('[CheckRunning]\nCloseEXE=FreeCrawl SEO Tool.exe\n\n[MainDirectories]\nRemoveAppDirectory=true\nRemoveOtherDirectory=true\n',encoding='utf-8')
    (appinfo/'Launcher'/'README.txt').write_text(
        'This independent package uses a compiled native C++ launcher, NOT PortableApps.com Launcher.\n'
        'Entry point: ../../../FreeCrawlPortable.exe\n'
        'Source code: Other/Source/FreeCrawlPortable.cpp in this package.\n'
        'An upstream Electron startup patch puts userData/sessionData under Data/Profile.\n'
        'No launcher.ini is used or required by this custom executable.\n',encoding='utf-8')
    builder_root=Path(__file__).resolve().parent.parent
    shutil.copy2(builder_root/'launcher/FreeCrawlPortable.cpp',notices/'FreeCrawlPortable.cpp')
    shutil.copy2(builder_root/'launcher/CMakeLists.txt',notices/'Launcher-CMakeLists.txt')
    shutil.copy2(builder_root/'scripts/patch_source.py',notices/'Portable-Patch-Source.py')
    meta={'upstream_repo':'https://github.com/kemalai/FreeCrawl-SEO-Tool',
          'upstream_version':a.version,'upstream_commit':a.commit,
          'builder_revision':a.revision,'upstream_license':'MIT',
          'package_type':'independent PortableApps ZIP plus genuine PortableApps.com Installer-generated PAF; not certified',
          'data_location':'Data/Profile (application profile); Data/Cache, Data/Temp',
          'launcher':'Compiled Windows x64 C++ launcher'}
    (notices/'BUILD-INFO.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    (stage/'help.html').write_text('<!doctype html><meta charset="utf-8"><title>FreeCrawl Portable</title>'
          '<h1>FreeCrawl SEO Tool Portable</h1><p>Launch FreeCrawlPortable.exe. '
          'Keep the Data folder when updating. This is an independent portable build, not an official PortableApps.com release.</p>'
          '<p>Copyright (c) 2026 Kemal Acar. Upstream source and MIT license are listed under Other/Source.</p>',encoding='utf-8')
    output.mkdir(parents=True,exist_ok=True)
    archive=output/f'FreeCrawlPortable_v{a.version}_r{a.revision}_win64.zip'
    if archive.exists(): archive.unlink()
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for path in sorted(stage.rglob('*')):
            arcname=path.relative_to(stage.parent).as_posix()
            if path.is_dir():
                if path.name in ('Data','DefaultData'):
                    z.writestr(arcname+'/',b'')
                continue
            z.write(path,arcname)
    print(f'Packaged {archive} ({archive.stat().st_size:,} bytes)')
    if archive.stat().st_size >= 2*1024**3:
        raise RuntimeError('Publisher rejects archives >= 2 GiB')

if __name__=='__main__':
    main()
