"""Static PE / PortableApps metadata / relocation-safe archive validation."""
from __future__ import annotations
import argparse, configparser, io, struct, zipfile
from pathlib import Path
from PIL import Image

ROOT='FreeCrawlPortable/'

def check_pe(payload:bytes,label:str):
    if len(payload)<256 or payload[:2]!=b'MZ': raise RuntimeError(label+': missing MZ header')
    off=struct.unpack_from('<I',payload,0x3c)[0]
    if off<64 or off+6>len(payload) or payload[off:off+4]!=b'PE\0\0':
        raise RuntimeError(label+': invalid PE signature')
    if struct.unpack_from('<H',payload,off+4)[0]!=0x8664:
        raise RuntimeError(label+': not a genuine x64 PE')

def main():
    p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('--version',required=True)
    a=p.parse_args()
    zpath=Path(a.archive)
    with zipfile.ZipFile(zpath) as z:
        bad=z.testzip()
        if bad: raise RuntimeError('Corrupt ZIP member: '+bad)
        names=z.namelist()
        if len(names)!=len(set(names)): raise RuntimeError('Duplicate ZIP member')
        for name in names:
            if not name.startswith(ROOT) or '..' in name.split('/') or '\\' in name:
                raise RuntimeError('Unsafe ZIP path: '+name)
        required=[ROOT+'FreeCrawlPortable.exe',
                  ROOT+'App/FreeCrawl/FreeCrawl SEO Tool.exe',
                  ROOT+'App/FreeCrawl/resources/app.asar',
                  ROOT+'App/AppInfo/appinfo.ini',
                  ROOT+'App/AppInfo/installer.ini',
                  ROOT+'App/AppInfo/appicon.ico',
                  ROOT+'Data/',
                  ROOT+'Other/Source/UPSTREAM-LICENSE.txt',
                  ROOT+'Other/Source/FreeCrawlPortable.cpp',
                  ROOT+'Other/Source/BUILD-INFO.json']
        for member in required:
            if member not in names: raise RuntimeError('Required package member missing: '+member)
        for n in (16,32,75,128,256):
            name=ROOT+f'App/AppInfo/appicon_{n}.png'
            if name not in names: raise RuntimeError('Missing icon: '+name)
            with Image.open(io.BytesIO(z.read(name))) as img:
                if img.size!=(n,n): raise RuntimeError('Invalid PNG icon dimensions')
        check_pe(z.read(ROOT+'FreeCrawlPortable.exe'),'PortableApps launcher')
        # Read only the first 4 KiB for the large Electron executable.
        with z.open(ROOT+'App/FreeCrawl/FreeCrawl SEO Tool.exe') as f:
            check_pe(f.read(4096),'Electron executable')
        cfg=configparser.ConfigParser(interpolation=None)
        cfg.read_string(z.read(ROOT+'App/AppInfo/appinfo.ini').decode('utf-8'))
        assert cfg.get('Format','Type')=='PortableApps.comFormat'
        assert cfg.get('Format','Version')=='3.9'
        assert cfg.get('Control','Start')=='FreeCrawlPortable.exe'
        assert cfg.get('Details','AppID')=='FreeCrawlPortable-vhick'
        installer=configparser.ConfigParser(interpolation=None)
        installer.read_string(z.read(ROOT+'App/AppInfo/installer.ini').decode('utf-8'))
        assert installer.get('MainDirectories','RemoveAppDirectory')=='true'
        assert not installer.has_option('MainDirectories','RemoveDataDirectory')
        assert cfg.get('Version','DisplayVersion').startswith(a.version+' ')
        for member in names:
            if member.startswith(ROOT+'Data/') and member!=ROOT+'Data/':
                raise RuntimeError('New packages must have an empty Data directory')
        meta=z.read(ROOT+'Other/Source/BUILD-INFO.json').decode('utf-8')
        if a.version not in meta: raise RuntimeError('Missing upstream version in provenance')
        if 'MIT License' not in z.read(ROOT+'Other/Source/UPSTREAM-LICENSE.txt').decode('utf-8'):
            raise RuntimeError('Upstream MIT notice missing')
    print('PASS: ZIP integrity, x64 PE launchers, icons, 3.9 metadata, license, empty Data, source provenance.')
    print('Note: static checks do not prove actual GUI launch or PortableApps Menu discovery.')

if __name__=='__main__':
    main()
