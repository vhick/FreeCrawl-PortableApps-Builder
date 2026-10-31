"""Static guard for the PowerShell curl-array regression on Windows hosts.

This does not replace execution on the Windows runner.
"""
from pathlib import Path

script = (Path(__file__).parent / 'acquire_installer.ps1').read_text(encoding='utf-8')
assert "Join-Path $env:WINDIR 'System32\\curl.exe'" in script
assert 'Select-Object -First 1' in script
assert '& $curlExe --fail' in script
assert '& $curl.Source' not in script
assert 'Get-FileHash' in script
assert '689456f1fb1320c45e82a077afe6b87fb388fd3f75c41d9ee9ce8d45f3966b67' in script
assert 'netix.dl.sourceforge.net' in script
print('PASS: one curl executable, pinned official installer checksum, multiple mirrors')
