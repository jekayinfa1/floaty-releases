"""Transport verified installer bytes; never compile or execute downloaded files."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

REPO = 'jekayinfa1/floaty-releases'
assert os.environ['GITHUB_REPOSITORY'] == REPO
source, target = os.environ['SOURCE_TAG'], os.environ['TARGET_TAG']
assert re.fullmatch(r'upload-windows-\d+\.\d+\.\d+-[0-9]+', source)
assert re.fullmatch(r'v\d+\.\d+\.\d+', target)
version = target[1:]
allowed = {
    f'Floaty-OS-{version}-Setup-x64.exe',
    f'Floaty-OS-{version}-Portable-x64.exe',
    f'Floaty-OS-{version}-Setup-x64.exe.blockmap',
    'Floaty-OS-Setup.exe', 'Floaty-OS-Portable.exe', 'latest.yml',
}

def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)

def digest(file):
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def check(file, item):
    assert file.stat().st_size == item['size'], file.name + ' size mismatch'
    assert digest(file) == item['sha256'], file.name + ' digest mismatch'

with tempfile.TemporaryDirectory(prefix='floaty-installer-') as directory:
    root = Path(directory)
    info = json.loads(gh('api', f'repos/{REPO}/releases/tags/{source}'))
    assert info['draft'], 'Chunk source must be a draft release'
    published = json.loads(gh('api', f'repos/{REPO}/releases/tags/{target}'))
    assert not published['draft'], 'Target must already be public'
    gh('release', 'download', source, '--repo', REPO, '--dir', str(root))
    manifest = json.loads((root / 'manifest.json').read_text())
    assert manifest['version'] == version
    assert {f['name'] for f in manifest['files']} == allowed
    assert len(manifest['files']) == len(allowed)
    output = root / 'output'
    output.mkdir()
    for item in manifest['files']:
        assert 0 < item['size'] < 2 * 1024**3
        assert re.fullmatch(r'[a-f0-9]{64}', item['sha256'])
        filename = output / item['name']
        if 'aliasOf' in item:
            assert item['aliasOf'] in allowed
            source_file = output / item['aliasOf']
            check(source_file, item)
            filename.hardlink_to(source_file)
        else:
            parts = item['parts']
            assert 0 < len(parts) <= 128
            with filename.open('wb') as result:
                for i, part in enumerate(parts):
                    assert part['name'] == item['name'] + f'.part-{i:04d}'
                    assert 0 < part['size'] <= 16 * 1024**2
                    assert re.fullmatch(r'[a-f0-9]{64}', part['sha256'])
                    part_file = root / part['name']
                    check(part_file, part)
                    with part_file.open('rb') as stream:
                        while chunk := stream.read(1024**2):
                            result.write(chunk)
        check(filename, item)
        print('Verified reconstructed ' + item['name'], flush=True)
    for item in manifest['files']:
        for attempt in range(4):
            release = json.loads(gh('api', f'repos/{REPO}/releases/tags/{target}'))
            existing = next((a for a in release['assets'] if a['name'] == item['name']), None)
            if existing:
                assert existing['state'] == 'uploaded'
                assert existing['size'] == item['size']
                assert existing['digest'] == 'sha256:' + item['sha256']
                break
            result = subprocess.run(['gh', 'release', 'upload', target, str(output / item['name']), '--repo', REPO])
            time.sleep(2)
        else:
            raise RuntimeError('Upload did not verify: ' + item['name'])
        print('Verified published ' + item['name'], flush=True)
    print('Windows assets published. Global latest and website promotion are separate explicit steps.')
