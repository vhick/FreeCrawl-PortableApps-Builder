"""Offline regression tests for the r5 filename/location mistake."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import patch
import locate_official_paf

with TemporaryDirectory() as tmp:
    root=Path(tmp)
    path=root/'FreeCrawl_SEO_Tool_Portable_1.1.2.paf.exe'
    buf=bytearray(200_000)
    buf[:2]=b'MZ'
    buf[0x3c:0x40]=(0x80).to_bytes(4,'little')
    buf[0x80:0x84]=b'PE\0\0'
    path.write_bytes(buf)
    start=datetime.now(timezone.utc)-timedelta(seconds=2)
    mock=SimpleNamespace(returncode=0,stdout='Path = FreeCrawlPortable.exe\nPath = App/AppInfo/appinfo.ini',stderr='')
    with patch('locate_official_paf.subprocess.run',return_value=mock):
        found=locate_official_paf.locate([root],start,Path('7z.exe'))
        assert found==[path],found
        (root/'AnotherInstaller.paf.exe').write_bytes(buf)
        found=locate_official_paf.locate([root],start,Path('7z.exe'))
        assert len(found)==2,found
        found=locate_official_paf.locate([root],datetime.now(timezone.utc)+timedelta(minutes=5),Path('7z.exe'))
        assert not found,found
    print('PASS: official PAF output discovery handles metadata-derived filenames, ambiguity, and stale files')
