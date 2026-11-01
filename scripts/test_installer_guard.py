"""Static regression test: do not launch vendor GUI bootstrap, always bound packager runtime."""
from pathlib import Path

source = Path(__file__).with_name('build_installer.ps1').read_text(encoding='utf-8')
assert 'Invoke-BoundedProgram' in source
assert "-TimeoutSeconds 120" in source, '7-Zip extraction must have a limit'
assert "-TimeoutSeconds 480" in source, 'Official builder must have a limit'
assert 'PortableApps.comInstaller.exe' in source
assert 'Get-FileHash' in source and '689456f1fb1320c45e82a077afe6b87fb388fd3f75c41d9ee9ce8d45f3966b67' in source
assert 'Start-Process -FilePath $toolDownload' not in source, 'Do not run vendor package GUI'
assert "-Arguments @('x', $toolDownload" in source, 'Extract NSIS archive with 7-Zip'
assert "Invoke-BoundedProgram -Exe $builderExe" in source, 'Execute original vendor tool, not custom NSIS'
assert "makensis" not in source.lower(), 'Not a third-party custom NSIS PAF'
print('PASS: verified 7-Zip extraction, official vendor builder, no GUI bootstrap, timeouts')
