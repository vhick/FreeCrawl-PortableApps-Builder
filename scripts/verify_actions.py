#!/usr/bin/env python3
"""Fail closed when pinned third-party action interfaces change.
No third-party action is downloaded for local execution by this script.
"""
from __future__ import annotations
import hashlib
import urllib.request

ACTIONS = {
    'Package Builder v1.0.0': (
        'https://raw.githubusercontent.com/vhick/Portable-Package-Builder/0112c35580e83b37eb8757ebcb949274e1631a04/action.yml',
        ['source-dir', 'output-dir', 'engine', 'running-exe', 'timeout-seconds',
         'package-revision', 'official-tool-url', 'official-tool-sha256',
         'installer-file', 'installer-sha256', 'app-id', 'app-version']),
    'Publisher v1.1.1': (
        'https://raw.githubusercontent.com/vhick/portable-release-publisher/cb64f86ac2d8c67506db5832de07f9ff58cbeaeb/action.yml',
        ['files', 'tag', 'release-title', 'tag-prefix', 'keep-releases', 'prune', 'dry-run']),
}


def main():
    for name, (url, fields) in ACTIONS.items():
        request = urllib.request.Request(url, headers={'User-Agent': 'FreeCrawl-PortableApps-Builder-b1r1'})
        with urllib.request.urlopen(request, timeout=40) as response:
            raw = response.read()
        text = raw.decode('utf-8')
        if 'using: composite' not in text:
            raise RuntimeError(f'{name}: unexpected action execution mode')
        if 'inputs:' not in text:
            raise RuntimeError(f'{name}: missing inputs')
        for field in fields:
            if not any(line.startswith('  ' + field + ':') for line in text.splitlines()):
                raise RuntimeError(f'{name}: action.yml missing required interface: {field}')
        print(f'PINNED ACTION VERIFIED: {name}, action.yml SHA256={hashlib.sha256(raw).hexdigest()}')
    print('Action commits are immutable pins resolved from the requested tags; action code is not vendored.')


if __name__ == '__main__':
    main()
