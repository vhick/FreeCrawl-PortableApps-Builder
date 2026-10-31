"""Small fail-closed source patch. Uses Electron's documented app.setPath API.
The marker is checked on every stable version: incompatible source must fail, not silently leak data.
"""
import argparse
from pathlib import Path

MARKER='logger.installGlobalHooks();'
PATCH='''// BEGIN FreeCrawl independent PortableApps data relocation (builder r1)
// This runs before requestSingleInstanceLock and app.whenReady().
// No user profile is imported, altered or overwritten.
if (process.platform === 'win32' && process.env['FREECRAWL_PORTABLE_PROFILE']) {
  const portableProfile = resolvePath(process.env['FREECRAWL_PORTABLE_PROFILE']);
  const chromiumProfile = join(portableProfile, 'Chromium');
  mkdirSync(portableProfile, { recursive: true });
  mkdirSync(chromiumProfile, { recursive: true });
  const portableTemp = resolvePath(process.env['TEMP'] ?? join(portableProfile, 'Temp'));
  mkdirSync(portableTemp, { recursive: true });
  app.setPath('temp', portableTemp);
  app.setPath('userData', portableProfile);
  app.setPath('sessionData', chromiumProfile);
}
// END FreeCrawl independent PortableApps data relocation
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('upstream')
    args=parser.parse_args()
    base=Path(args.upstream)
    target=base/'apps/desktop/src/main/index.ts'
    src=target.read_text(encoding='utf-8')
    if src.count(MARKER)!=1:
        raise RuntimeError('Source bootstrap changed; refusing unsafe patch')
    if 'BEGIN FreeCrawl independent PortableApps' in src:
        raise RuntimeError('Already patched')
    if 'app.requestSingleInstanceLock()' not in src or 'app.whenReady()' not in src:
        raise RuntimeError('Electron lifecycle unexpectedly changed')
    # PATCH is immediately before logging/locking. Main imports are evaluated earlier.
    target.write_text(src.replace(MARKER,PATCH+MARKER,1),encoding='utf-8')
    print('Applied guarded Electron userData/sessionData patch:',target)

if __name__=='__main__':
    main()
