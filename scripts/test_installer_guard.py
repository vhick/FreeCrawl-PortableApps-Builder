"""r6 static smoke and regression test of official-first and honest fallback behavior."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent
source=(root/'scripts/build_installer.ps1').read_text(encoding='utf-8')
locator=(root/'scripts/locate_official_paf.py').read_text(encoding='utf-8')
nsis=(root/'installer/FreeCrawlPortable.nsi').read_text(encoding='utf-8')
workflow=(root/'.github/workflows/build-portableapps.yml').read_text(encoding='utf-8')
assert 'Invoke-BoundedProgram' in source
assert '-TimeoutSeconds 120' in source
assert '-TimeoutSeconds 480' in source
assert '689456f1fb1320c45e82a077afe6b87fb388fd3f75c41d9ee9ce8d45f3966b67' in source
assert "-Arguments @('x', $toolDownload" in source
assert 'locate_official_paf.py' in source
assert 'build_nsis_fallback.ps1' in source
assert "engine=$officialStatus" in source
assert "'fallback'" in source
assert "'appinfo.ini'" in locator and "'freecrawlportable.exe'" in locator
assert r'RMDir /r "$INSTDIR\FreeCrawlPortable\App"' in nsis
assert r'RMDir /r "$INSTDIR\FreeCrawlPortable\Other"' in nsis
assert r'RMDir /r "$INSTDIR\FreeCrawlPortable\Data"' not in nsis
assert r'CreateDirectory "$INSTDIR\FreeCrawlPortable\Data"' in nsis
assert "BUILDER_REV: '6'" in workflow
assert "v1.1.1" in workflow
assert 'actions/upload-artifact' not in workflow
print('PASS: r6 official-output discovery, independently disclosed NSIS fallback, Data preservation, bounded executions')
