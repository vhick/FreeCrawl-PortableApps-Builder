"""r7 lightweight regression checks without downloading or compiling the app."""
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util

root=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('pafcheck',root/'scripts/verify_paf_payload.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with TemporaryDirectory() as temporary:
    stage=Path(temporary)
    appinfo=stage/'App'/'AppInfo';appinfo.mkdir(parents=True)
    (stage/'Data').mkdir()
    (appinfo/'installer.ini').write_text('[MainDirectories]\nRemoveAppDirectory=true\nRemoveOtherDirectory=true\nRemoveDataDirectory=false\n')
    (appinfo/'appinfo.ini').write_text('[Control]\nStart=FreeCrawlPortable.exe\n')
    module.verify_staged_policy(stage)
    records=[f'Path = folder/{x}' for x in module.REQUIRED]
    records.extend(f'Path = file-{n}.dll' for n in range(8))
    module.verify_manifest('\n'.join(records))
    (appinfo/'installer.ini').write_text('[MainDirectories]\nRemoveAppDirectory=true\nRemoveOtherDirectory=true\nRemoveDataDirectory=true\n')
    try: module.verify_staged_policy(stage)
    except RuntimeError: pass
    else: raise AssertionError('Incorrect remove Data setting was accepted')
    (appinfo/'installer.ini').write_text('[MainDirectories]\nRemoveAppDirectory=true\nRemoveOtherDirectory=true\nRemoveDataDirectory=false\n')
    records.remove('Path = folder/app.asar')
    try: module.verify_manifest('\n'.join(records))
    except RuntimeError: pass
    else: raise AssertionError('Missing app.asar was accepted')
flow=(root/'.github/workflows/build-portableapps.yml').read_text()
assert "BUILDER_REV: '7'" in flow
assert 'verify_paf_payload.py' in flow
assert 'verify_installer.ps1' not in flow
assert 'actions/upload-artifact' not in flow
print('PASS: r7 positive/negative payload checks, Data retention guard and no GUI installation automation')
