"""One-shot bootstrap for a fresh clone: Python packages + the external tools from their official GitHub releases.

    python setup.py            # vgmstream, wwiser, DepotDownloader -> external/
    python setup.py --no-dd    # skip DepotDownloader (only needed to fetch other game builds)

RPKG-Tool is NOT required by any script here (the RPKG format, XOR key, LZ4 and the manifest XTEA keys are
implemented in tools/). It is only useful for its hash list (resource names); get the *first-light* branch CI
build from https://github.com/glacier-modding/RPKG-Tool if you want that.
"""
import io, json, os, subprocess, sys, urllib.request, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
EXT = os.path.join(ROOT, 'external')
TOOLS = [  # (repo, asset name, target dir, member filter)
    ('vgmstream/vgmstream', 'vgmstream-win64.zip', 'vgmstream', None),
    ('bnnm/wwiser', 'wwiser.pyz', 'wwiser', None),
    ('SteamRE/DepotDownloader', 'DepotDownloader-windows-x64.zip', 'DepotDownloader', None),
]

def gh_asset(repo, name):
    with urllib.request.urlopen(f'https://api.github.com/repos/{repo}/releases/latest', timeout=60) as r:
        rel = json.load(r)
    for a in rel['assets']:
        if a['name'] == name:
            return rel['tag_name'], a['browser_download_url']
    raise SystemExit(f'{repo}: asset {name} not found in release {rel.get("tag_name")}')

def main():
    skip_dd = '--no-dd' in sys.argv
    print('pip: numpy scipy soundfile lz4')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', '-q', 'numpy', 'scipy', 'soundfile', 'lz4'], check=False)
    for repo, asset, target, _ in TOOLS:
        if skip_dd and target == 'DepotDownloader':
            continue
        dest = os.path.join(EXT, target)
        if os.path.exists(dest) and os.listdir(dest):
            print(f'{target}: already present, skipping')
            continue
        tag, url = gh_asset(repo, asset)
        print(f'{target}: downloading {asset} ({tag})')
        data = urllib.request.urlopen(url, timeout=300).read()
        os.makedirs(dest, exist_ok=True)
        if asset.endswith('.zip'):
            zipfile.ZipFile(io.BytesIO(data)).extractall(dest)
        else:
            open(os.path.join(dest, asset), 'wb').write(data)
    print('done. Next: python rebuild.py "<game>/Runtime"')

if __name__ == '__main__':
    main()
