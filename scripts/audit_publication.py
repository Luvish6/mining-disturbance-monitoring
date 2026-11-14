"""Audit the complete staged index or a commit tree before public Git publication.

Heuristic checks complement manual licensing/privacy review; never print secret values.
"""
import argparse
import re
import subprocess
from pathlib import PurePosixPath

MAX_FILE = 1_048_576
MAX_TOTAL = 10_485_760
ROOT_FILES = {'.gitignore', '.gitattributes', '.env.example', 'AGENTS.md', 'README.md',
              'main.py', 'phase2.py', 'phase3.py', 'phase3_data.py', 'check_boundary.py',
              'requirements.txt', 'requirements-phase3.txt'}
ALLOWED_DIRS = {'src', 'tests', 'config', 'gee_js', 'docs', 'scripts', '.githooks'}
TEXT_SUFFIXES = {'.py', '.js', '.md', '.txt', '.csv', '.json', '.yml', '.yaml', '.toml', '.sh'}
BLOCKED_SUFFIXES = {'.zip', '.7z', '.rar', '.gz', '.tar', '.tif', '.tiff', '.jp2', '.img',
                    '.vrt', '.nc', '.hdf', '.h5', '.gpkg', '.shp', '.kml', '.kmz', '.png',
                    '.jpg', '.jpeg', '.pdf', '.npy', '.npz', '.pkl', '.pt', '.pth', '.joblib',
                    '.onnx', '.pem', '.key', '.p12', '.pfx'}
PATTERNS = {
 'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'GitHub credential': re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})'),
 'AWS access key': re.compile(r'(?:AKIA|ASIA)[A-Z0-9]{16}'),
 'Google API key': re.compile(r'AIza[A-Za-z0-9_-]{30,}'),
 'bearer credential': re.compile(r'(?i)bearer\s+[A-Za-z0-9_\-.]{24,}'),
 'session URL': re.compile(r'(?i)(?:[?;&]|%3b)(?:jsessionid|access_token|refresh_token|api_key)(?:=|%3d)'),
 'private local path': re.compile(r'(?i)(?<![a-z0-9])(?:[a-z]:[\\/](?:Users|Projects)[\\/]|/(?:Users|home)/[^\s/]+/)'),
}
ASSIGNMENT = re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password)\s*[:=]\s*['\"]([^'\"\r\n]{8,})['\"]")

def git(*args):
    return subprocess.check_output(['git', *args])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--staged', action='store_true')
    group.add_argument('--ref', help='Commit/tree to audit; default is entire staged index')
    args = parser.parse_args()
    if args.ref:
        ref = git('rev-parse', '--verify', args.ref + '^{commit}').decode().strip()
        paths = git('ls-tree', '-r', '--name-only', '-z', ref).decode().split('\0')
        prefix = ref + ':'
    else:
        paths = git('ls-files', '-z').decode().split('\0')
        prefix = ':'
    failures, total, count = [], 0, 0
    for name in filter(None, paths):
        path = PurePosixPath(name)
        if name == 'outputs/.gitkeep':
            content = git('show', prefix + name)
            if content: failures.append((name, 'placeholder must be empty'))
            count += 1
            continue
        allowed = name in ROOT_FILES or (path.parts[0] in ALLOWED_DIRS and
                   (path.suffix.lower() in TEXT_SUFFIXES or path.parts[0] == '.githooks'))
        if path.parts[0] == 'frontend':
            allowed = (name in {'frontend/.gitignore', 'frontend/index.html', 'frontend/package.json',
                                'frontend/package-lock.json', 'frontend/tsconfig.json'}
                       or (path.parts[1:2] == ('src',) and path.suffix in {'.ts', '.tsx', '.css'}))
        if not allowed: failures.append((name, 'outside reviewed source/docs publication scope'))
        if (path.suffix.lower() in BLOCKED_SUFFIXES or
            any(p in {'__pycache__', '.venv', 'secrets', 'credentials', 'raw', 'licensed_imagery', 'restricted'} for p in path.parts) or
            (path.name.startswith('.env') and name != '.env.example')):
            failures.append((name, 'protected data/credential/binary path'))
        content = git('show', prefix + name)
        count += 1; total += len(content)
        if len(content) > MAX_FILE: failures.append((name, 'exceeds 1 MiB review ceiling'))
        if b'\0' in content: failures.append((name, 'binary content')); continue
        try: text = content.decode('utf-8-sig')
        except UnicodeDecodeError: failures.append((name, 'non-UTF8 content requires explicit review')); continue
        for rule, pattern in PATTERNS.items():
            if pattern.search(text): failures.append((name, rule))
        for match in ASSIGNMENT.finditer(text):
            value = match.group(1)
            if not re.search(r'(?i)(example|placeholder|synthetic|your[_ -]|<[^>]+>)', value):
                failures.append((name, 'possible assigned credential; inspect locally'))
    if total > MAX_TOTAL: failures.append(('<tree>', 'exceeds 10 MiB review ceiling'))
    if failures:
        for name, reason in failures: print(f'BLOCKED: {name}: {reason}')
        raise SystemExit(1)
    print(f'Publication audit passed: {count} files, {total} bytes. Manual rights/research review remains required.')

if __name__ == '__main__':
    main()
