"""One isolated D: CUDA setup through a bounded official-source wheel proxy."""
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote

from src.phase25.setup_transfer import Transfers,ROOT,serve
import src.phase25.setup_transfer as transport
from packaging.tags import cpython_tags,compatible_tags

ENV=Path('D:/ResearchEnvironments/minechange-india-gpu-v1')


def resource_gate():
    class Mem(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in ['total','available','page_total','page_available','virtual_total','virtual_available','extended']]
    m=Mem();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    free=m.available/2**30
    if free<8:raise RuntimeError(f'RAM_GATE {free:.3f}GiB <8GiB; no heavy setup')
    if shutil.disk_usage('D:/').free<20*2**30 or shutil.disk_usage('C:/').free<10*2**30:raise RuntimeError('Disk gate failed')
    print(f'RESOURCE_GATE_PASS available_RAM={free:.3f}GiB',flush=True)
    return free


def links(name,version,minor=12):
    class Parser(HTMLParser):
        def __init__(self):super().__init__();self.f=[]
        def handle_starttag(self,t,a):
            d=dict(a)
            if t!='a' or 'href' not in d:return
            u=d['href'];n=unquote(urlsplit(u).path.rsplit('/',1)[-1])
            if n==f'{name}-{version}-cp3{minor}-cp3{minor}-win_amd64.whl':
                self.f.append(dict(filename=n,url=u.split('#')[0],sha256=u.split('#sha256=')[-1],requires_python=d.get('data-requires-python'),metadata=d.get('data-dist-info-metadata')))
    p=Parser();p.feed((ROOT/('official-'+name+'-cu128-index.html')).read_text())
    if len(p.f)!=1:raise ValueError('Official pinned wheel identity unavailable')
    return p.f


def existing_python():
    python=ENV/'Scripts/python.exe'
    if not python.is_file():raise RuntimeError('User-provided isolated venv required; no recreation')
    version=subprocess.check_output([str(python),'--version'],text=True).strip()
    if version!='Python 3.12.10':raise RuntimeError('Expected supplied Python3.12.10; no substitution')
    return python


def run():
    resource_gate();t=Transfers()
    python=existing_python()
    transport.TAGS=set(cpython_tags((3,12),abis=['cp312'],platforms=['win_amd64']))|set(compatible_tags((3,12),interpreter='cp312',platforms=['win_amd64']))
    pinned={'torch':links('torch','2.11.0+cu128'),'torchvision':links('torchvision','0.26.0+cu128')}
    receipt=json.loads((ROOT/'antlr-approved-build.json').read_bytes())
    wheel=ROOT/'antlr4_python3_runtime-4.9.3-py3-none-any.whl'
    entry=dict(filename=wheel.name,url='approved-local:antlr4-4.9.3',local_path=str(wheel),sha256=receipt['wheel_sha256'])
    transport.approved_local_wheel(entry)
    pinned['antlr4-python3-runtime']=[entry]
    (ROOT/'pinned-cuda-wheels.json').write_text(json.dumps(pinned,indent=2),encoding='utf-8')
    env=os.environ.copy();env.update(UV_CACHE_DIR=str(ROOT/'uv-cache'),UV_PYTHON_DOWNLOADS='never',UV_CONCURRENT_DOWNLOADS='1',UV_CONCURRENT_BUILDS='1',UV_HTTP_RETRIES='0',UV_HTTP_TIMEOUT='1800',TMP=str(ROOT/'tmp'),TEMP=str(ROOT/'tmp'),PIP_CACHE_DIR=str(ROOT/'pip-cache'))
    (ROOT/'tmp').mkdir(exist_ok=True)
    req=ROOT/'requirements.in';req.write_text('torch==2.11.0+cu128\ntorchvision==0.26.0+cu128\nterratorch==1.2.14\n',encoding='utf-8')
    server,errors=serve(t,pinned)
    try:
        lock=ROOT/'requirements-py312.lock'
        if not lock.exists():
            p=subprocess.run(['uv','pip','compile',str(req),'--python',str(ENV/'Scripts/python.exe'),'--index-url','http://127.0.0.1:18765/simple','--allow-insecure-host','127.0.0.1','--no-build','--generate-hashes','--no-emit-index-url','-o',str(lock)],env=env,stdout=(ROOT/'resolve-python312.log').open('a'),stderr=subprocess.STDOUT)
            if p.returncode or errors:raise RuntimeError('Resolution failed; inspect local log, no source builds')
        resource_gate()
        p=subprocess.run(['uv','pip','sync','--python',str(ENV/'Scripts/python.exe'),str(lock),'--index-url','http://127.0.0.1:18765/simple','--allow-insecure-host','127.0.0.1','--no-build','--require-hashes'],env=env,stdout=(ROOT/'install-python312.log').open('a'),stderr=subprocess.STDOUT)
        if p.returncode or errors:raise RuntimeError('Bounded install failed; preserve cache and receipt')
        print('ISOLATED_SETUP_COMPLETE',flush=True)
        (ROOT/'setup-complete.json').write_text(json.dumps(dict(python=subprocess.check_output([str(python),'--version'],text=True).strip(),torch='2.11.0+cu128',torchvision='0.26.0+cu128',terratorch='1.2.14',dependency_charged=t.used('dependency'),lock_sha256=hashlib.sha256(lock.read_bytes()).hexdigest()),indent=2))
    finally:server.shutdown()


def bootstrap312():
    resource_gate();t=Transfers();server,errors=serve(t,{})
    env=os.environ.copy();env.update(UV_CACHE_DIR=str(ROOT/'uv-cache'),UV_HTTP_RETRIES='0',UV_HTTP_TIMEOUT='1800',TMP=str(ROOT/'tmp'),TEMP=str(ROOT/'tmp'))
    try:
        subprocess.run(['uv','python','install','3.12','--install-dir',str(ROOT/'python'),'--no-bin','--no-registry','--mirror','http://127.0.0.1:18765/python'],env=env,check=True)
        if errors:raise RuntimeError('Runtime mirror failure')
    finally:server.shutdown()


if __name__=='__main__':
    import sys
    if '--bootstrap312' in sys.argv:raise RuntimeError('Runtime acquisition disabled: reuse supplied venv')
    else:run()
