"""Preflight a checked-out user-owned shared publisher; do not execute unreviewed code here.
The authoritative ZIP + PAF acceptance test is the publisher's dry-run after packaging.
"""
from pathlib import Path
import sys
try:
    import yaml
except ImportError:
    raise SystemExit('Install PyYAML to inspect the publisher action')

publisher=Path('.publisher')
action=publisher/'action.yml'
script=publisher/'scripts/publish.py'
if not action.is_file() or not script.is_file():
    raise SystemExit('Shared publisher checkout must contain action.yml and scripts/publish.py')
yml=yaml.safe_load(action.read_text(encoding='utf-8'))
inputs=yml.get('inputs') or {}
for field in ('files','tag','release-title','prune','dry-run','keep-releases'):
    if field not in inputs:
        raise SystemExit('Publisher is missing its expected input: '+field)
source=script.read_text(encoding='utf-8').lower()
if 'paf.exe' not in source:
    raise SystemExit('The selected publisher ref still appears ZIP-only. Push the PAF-capable code and select its new tag/ref before running this builder. Do NOT rewrite v1.0.1.')
if 'zip' not in source:
    raise SystemExit('Selected publisher no longer mentions ZIP support; inspect its updated compatibility.')
print('Publisher action inputs found and PAF handling appears in its source.')
print('The publisher will be invoked with dry-run=true on BOTH real packages to verify behavior before publication.')
