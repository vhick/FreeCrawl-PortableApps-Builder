"""Resolve the newest numeric stable published GitHub release (not branch HEAD)."""
import json, os, re, sys, urllib.request
from pathlib import Path

REPO = "kemalai/FreeCrawl-SEO-Tool"
STABLE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")

def github_json(url):
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'FreeCrawl-PortableApps-Builder',
        **({'Authorization': 'Bearer '+os.environ['GH_TOKEN']} if os.getenv('GH_TOKEN') else {}),
    })
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def main():
    releases = github_json(f'https://api.github.com/repos/{REPO}/releases?per_page=100')
    if not isinstance(releases,list):
        raise RuntimeError('Unexpected releases API response')
    eligible = [(tuple(map(int,STABLE.fullmatch(r['tag_name']).groups())),r)
                for r in releases
                if STABLE.fullmatch(r.get('tag_name','')) and not r.get('draft') and not r.get('prerelease')]
    if not eligible:
        raise RuntimeError('No stable x.y.z published upstream release. Refusing unreviewed HEAD fallback.')
    version_parts, release = max(eligible,key=lambda item:item[0])
    version='.'.join(map(str,version_parts))
    tag=release['tag_name']
    # Never pass an unvalidated tag to shell commands.
    if not STABLE.fullmatch(tag):
        raise RuntimeError('Unsafe upstream tag')
    rev=os.environ.get('BUILDER_REV','2')
    if not re.fullmatch(r'[1-9][0-9]*',rev):
        raise RuntimeError('BUILDER_REV must be a positive integer')
    output_tag=f'portable-freecrawl-v{version}-r{rev}'
    filename=f'FreeCrawlPortable_v{version}_r{rev}_win64.zip'
    pafname=f'FreeCrawlPortable_v{version}_r{rev}_win64.paf.exe'
    for key,val in [('upstream_tag',tag),('upstream_version',version),('release_tag',output_tag),('package_name',filename),('paf_name',pafname)]:
        print(f'{key}={val}')
    output=os.getenv('GITHUB_OUTPUT')
    if output:
        with open(output,'a',encoding='utf-8') as fh:
            for key,val in [('upstream_tag',tag),('upstream_version',version),('release_tag',output_tag),('package_name',filename),('paf_name',pafname)]:
                fh.write(f'{key}={val}\n')
    Path('build-info.json').write_text(json.dumps({'upstream_tag':tag,'upstream_version':version,'release_tag':output_tag,'package_name':filename,'paf_name':pafname},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    main()
