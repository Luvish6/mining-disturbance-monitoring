"""Exactly-one approved ANTLR4.9.3 build, without executing sdist build scripts."""
import ast
import base64
import csv
import hashlib
import io
import json
import tarfile
import zipfile
from pathlib import Path,PurePosixPath

from src.phase25.setup_transfer import Transfers,ROOT
from scripts.phase25d2_setup import resource_gate

SOURCE_SHA='f224469b4168294902bb1efa80a8bf7855f24c99aef99cbefc1bcd3cce77881b'
NAME='antlr4_python3_runtime';VERSION='4.9.3'


def audit(archive):
    with Path(archive).open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=SOURCE_SHA:raise ValueError('Approved source SHA mismatch')
    with tarfile.open(archive,'r:gz') as t:
        members=t.getmembers()
        if len(members)>1000 or sum(m.size for m in members)>2_000_000:raise ValueError('Unexpected archive bounds')
        files={}
        for m in members:
            p=PurePosixPath(m.name)
            if p.is_absolute() or '..' in p.parts or p.parts[0]!='antlr4-python3-runtime-4.9.3' or not(m.isdir() or m.isfile()):raise ValueError('Unsafe archive member')
            if m.isfile():files['/'.join(p.parts[1:])]=t.extractfile(m).read()
    tree=ast.parse(files['setup.py'])
    if len(tree.body)!=2 or not isinstance(tree.body[0],ast.ImportFrom) or tree.body[0].module!='setuptools':raise ValueError('Unexpected build script')
    call=tree.body[1].value
    if not isinstance(call,ast.Call) or not isinstance(call.func,ast.Name) or call.func.id!='setup':raise ValueError('Non-declarative build script')
    args={k.arg:ast.literal_eval(k.value) for k in call.keywords}
    if args['name']!='antlr4-python3-runtime' or args['version']!=VERSION or args['package_dir']!={'':'src'} or args['scripts']!=['bin/pygrun']:
        raise ValueError('Unexpected distribution identity/layout')
    if args['install_requires']!=["typing ; python_version<'3.5'"]:raise ValueError('Unexpected build/runtime dependency')
    package={p[4:]:data for p,data in files.items() if p.startswith('src/antlr4/')}
    if not package or any(not p.endswith('.py') for p in package):raise ValueError('Non-Python package contents')
    forbidden={'subprocess','socket','requests','urllib','http','ctypes'}
    for p,data in package.items():
        for n in ast.walk(ast.parse(data)):
            roots={a.name.split('.')[0] for a in n.names} if isinstance(n,ast.Import) else {n.module.split('.')[0]} if isinstance(n,ast.ImportFrom) and n.module else set()
            if roots&forbidden:raise ValueError('Unexpected runtime external/native import')
    return files,package,args


def build(archive,dest):
    if Path(dest).exists():raise ValueError('Approved wheel already exists; do not rebuild')
    files,package,args=audit(archive);di=f'{NAME}-{VERSION}.dist-info';payload=dict(package)
    meta=files['PKG-INFO'].decode().replace('Metadata-Version: 1.0','Metadata-Version: 2.1')
    meta=meta.rstrip()+'\nRequires-Dist: typing; python_version < "3.5"\n\n'
    payload[di+'/METADATA']=meta.encode();payload[di+'/WHEEL']=b'Wheel-Version: 1.0\nGenerator: minechange-audited-pure-python-1\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
    # Standard wheel script shebang normalization; the CLI is never executed during build.
    script=files['bin/pygrun'];lines=script.splitlines(keepends=True)
    if lines and lines[0].startswith(b'#!'):lines[0]=b'#!python\n'
    payload[f'{NAME}-{VERSION}.data/scripts/pygrun']=b''.join(lines)
    records=[]
    for p,data in sorted(payload.items()):records.append([p,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode(),str(len(data))])
    records.append([di+'/RECORD','','']);buf=io.StringIO(newline='');csv.writer(buf,lineterminator='\n').writerows(records);payload[di+'/RECORD']=buf.getvalue().encode()
    with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p,data in sorted(payload.items()):
            info=zipfile.ZipInfo(p,date_time=(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,data)
    with zipfile.ZipFile(dest) as z:
        if z.testzip() is not None or set(z.namelist())!=set(payload):raise ValueError('Wheel integrity failure')
        for p,data in payload.items():
            if z.read(p)!=data:raise ValueError('Wheel content mismatch')
    return dict(source_sha256=SOURCE_SHA,wheel_sha256=hashlib.sha256(Path(dest).read_bytes()).hexdigest(),wheel_bytes=Path(dest).stat().st_size,
        package_python_files=len(package),source_members=len(files),setup_py_executed=False,external_build_dependencies=[],native_binaries=False,
        runtime_dependencies=args['install_requires'],license=args['license'],script='official pygrun retained; standardized wheel shebang only',
        record_entries=len(records),status='AUDITED_APPROVED_PURE_PYTHON_WHEEL')


def run():
    resource_gate();t=Transfers();meta=json.loads(t.get('https://pypi.org/pypi/antlr4-python3-runtime/4.9.3/json').read_bytes())
    f=next(x for x in meta['urls'] if x['filename']=='antlr4-python3-runtime-4.9.3.tar.gz')
    if f['digests']['sha256']!=SOURCE_SHA:raise ValueError('Published source identity changed')
    archive=t.get(f['url'],expected=SOURCE_SHA);dest=ROOT/(f'{NAME}-{VERSION}-py3-none-any.whl');receipt=ROOT/'antlr-approved-build.json'
    if receipt.exists():
        r=json.loads(receipt.read_bytes())
        if not dest.exists() or hashlib.sha256(dest.read_bytes()).hexdigest()!=r['wheel_sha256']:raise ValueError('Built wheel changed')
        print(json.dumps(r));return
    r=build(archive,dest);receipt.write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))


if __name__=='__main__':run()
