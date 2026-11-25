"""Phase25D.2 official-source transfer ledger and loopback wheel-only resolver proxy."""
import hashlib
import json
import os
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,quote,unquote

import requests
from packaging.tags import cpython_tags,compatible_tags
from packaging.utils import parse_wheel_filename,canonicalize_name

ROOT=Path('D:/ResearchEnvironments/minechange-india-gpu-v1-cache')
CAPS={'dependency':12*2**30,'model':250_000_000}
HOSTS={'pypi.org','files.pythonhosted.org','download.pytorch.org','download-r2.pytorch.org','huggingface.co','cdn-lfs.huggingface.co','cdn-lfs-us-1.hf.co','cas-bridge.xethub.hf.co','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}
TAGS=set(cpython_tags((3,11),abis=['cp311'],platforms=['win_amd64']))|set(compatible_tags((3,11),interpreter='cp311',platforms=['win_amd64']))


class Transfers:
    def __init__(self):
        ROOT.mkdir(parents=True,exist_ok=True);self.path=ROOT/'transfers.json';self.lock=threading.RLock()
        self.rows=json.loads(self.path.read_bytes()) if self.path.exists() else []
        self.session=requests.Session()
        self.session.mount('https://',requests.adapters.HTTPAdapter(max_retries=0))
    def persist(self):
        p=self.path.with_suffix('.tmp');p.write_text(json.dumps(self.rows,indent=2),encoding='utf-8');os.replace(p,self.path)
    def used(self,kind):return sum(r['charged'] for r in self.rows if r['kind']==kind)
    def get(self,url,kind='dependency',expected=None):
        key=hashlib.sha256(url.encode()).hexdigest();target=ROOT/'files'/key;target.parent.mkdir(exist_ok=True)
        if target.exists():
            with target.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
            if expected and actual!=expected:raise ValueError('Cached source hash mismatch')
            if not any(r.get('state')=='COMPLETE' and r.get('sha256')==actual and (r.get('key')==key or (not r.get('key') and r.get('host')==urlsplit(url).hostname)) for r in self.rows):raise ValueError('Unverified cache entry')
            return target
        with self.lock:
            if target.exists():return self.get(url,kind,expected)
            original=url
            for hop in range(6):
                host=urlsplit(url).hostname
                if urlsplit(url).scheme!='https' or (host not in HOSTS and not (kind=='model' and host=='us.aws.cdn.hf.co')):raise ValueError('Unapproved source host')
                if self.used(kind)+16384>CAPS[kind]:raise RuntimeError('Transfer cap before request')
                row=dict(kind=kind,host=host,key=key,state='PENDING',received=0,charged=16384)
                self.rows.append(row);self.persist()
                response=self.session.get(url,headers={'Accept-Encoding':'identity'},stream=True,allow_redirects=False,timeout=(20,120))
                row['status']=response.status_code
                if response.status_code in (301,302,303,307,308):
                    row['state']='REDIRECT';row['redirect_host']=urlsplit(response.headers['Location']).hostname;self.persist();url=response.headers['Location'];response.close();continue
                response.raise_for_status()
                length=response.headers.get('Content-Length')
                if length is None:response.close();raise RuntimeError('Known response size required')
                length=int(length)
                if self.used(kind)+length>CAPS[kind]:response.close();raise RuntimeError('Transfer cap before body')
                row['charged']+=length;self.persist()
                temp=target.with_suffix('.part');h=hashlib.sha256()
                try:
                    with temp.open('wb') as f:
                        while row['received']<length:
                            b=response.raw.read(min(1024*1024,length-row['received']),decode_content=False)
                            if not b:break
                            if row['received']+len(b)>length:raise RuntimeError('Body exceeds declared length')
                            f.write(b);h.update(b);row['received']+=len(b)
                    if row['received']!=length:raise RuntimeError('Incomplete source body')
                    if expected and h.hexdigest()!=expected:raise ValueError('Published source checksum mismatch')
                    temp.replace(target);row.update(state='COMPLETE',sha256=h.hexdigest(),bytes=length);self.persist()
                    print(json.dumps(dict(source=host,kind=kind,bytes=length,charged_total=self.used(kind))),flush=True)
                    return target
                except BaseException:
                    row['state']='FAILED';row['charged']=16384+row['received'];self.persist();raise
                finally:response.close()
            raise RuntimeError('Redirect limit')


def compatible(filename):
    try:return bool(parse_wheel_filename(filename)[3]&TAGS)
    except ValueError:return False


def approved_local_wheel(entry):
    source=Path(entry['local_path']).resolve()
    if source.parent!=ROOT.resolve() or source.name!='antlr4_python3_runtime-4.9.3-py3-none-any.whl':
        raise ValueError('Only approved ANTLR local wheel')
    receipt=json.loads((ROOT/'antlr-approved-build.json').read_bytes())
    actual=hashlib.sha256(source.read_bytes()).hexdigest()
    if actual!=entry['sha256'] or actual!=receipt['wheel_sha256'] or receipt['source_sha256']!='f224469b4168294902bb1efa80a8bf7855f24c99aef99cbefc1bcd3cce77881b':
        raise ValueError('Approved wheel integrity failure')
    return source


def serve(transfer,torch_links,port=18765):
    mapping=ROOT/'source-links.json'
    urls=json.loads(mapping.read_bytes()) if mapping.exists() else {};simple={};errors=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_HEAD(self):
            try:
                path=unquote(urlsplit(self.path).path)
                _,_,token,filename=path.split('/',3)
                entry=urls[token]
                if not path.startswith('/file/') or filename!=entry['filename'] or not entry.get('local_path'):
                    self.send_error(405);return
                source=approved_local_wheel(entry)
                self.send_response(200);self.send_header('Content-Length',str(source.stat().st_size));self.send_header('Accept-Ranges','bytes');self.end_headers()
            except (ValueError,KeyError,FileNotFoundError):self.send_error(502)
        def do_GET(self):
            try:
                path=unquote(urlsplit(self.path).path)
                if path.startswith('/python/'):
                    tail=path.removeprefix('/python/')
                    if '..' in tail or 'cpython-3.12.' not in tail or 'windows' not in tail:raise ValueError('Only approved Python3.12 runtime archive')
                    source=transfer.get('https://github.com/astral-sh/python-build-standalone/releases/download/'+tail)
                    self.send_response(200);self.send_header('Content-Length',str(source.stat().st_size));self.end_headers()
                    with source.open('rb') as f:
                        while True:
                            block=f.read(1024*1024)
                            if not block:break
                            self.wfile.write(block)
                elif path.startswith('/simple/'):
                    with transfer.lock:
                        name=canonicalize_name(path.strip('/').split('/')[-1])
                        if name not in simple:
                            if name in torch_links:files=torch_links[name]
                            else:
                                source=transfer.get('https://pypi.org/simple/'+name+'/')
                                from html.parser import HTMLParser
                                class Links(HTMLParser):
                                    def __init__(self):super().__init__();self.files=[]
                                    def handle_starttag(self,tag,attrs):
                                        d=dict(attrs)
                                        if tag=='a' and 'href' in d:self.files.append(d)
                                parser=Links();parser.feed(source.read_text());files=[]
                                for d in parser.files:
                                    url=d['href'];filename=urlsplit(url).path.rsplit('/',1)[-1]
                                    if compatible(filename):files.append(dict(filename=filename,url=url.split('#')[0],sha256=url.split('#sha256=')[-1] if '#sha256=' in url else None,requires_python=d.get('data-requires-python'),metadata=d.get('data-dist-info-metadata') or d.get('data-core-metadata')))
                            links=[]
                            import html
                            for f in files:
                                if not compatible(f['filename']):continue
                                token=hashlib.sha256(f['url'].encode()).hexdigest();urls[token]=f
                                href=f'http://127.0.0.1:{port}/file/{token}/'+quote(f['filename'])
                                if f.get('sha256'):href+='#sha256='+f['sha256']
                                attrs=''
                                if f.get('requires_python'):attrs+=' data-requires-python="'+html.escape(f['requires_python'],quote=True)+'"'
                                if f.get('metadata'):attrs+=' data-dist-info-metadata="'+str(f['metadata'])+'"'
                                links.append('<a href="'+href+'"'+attrs+'>'+f['filename']+'</a>')
                            temp=mapping.with_suffix('.tmp');temp.write_text(json.dumps(urls),encoding='utf-8');os.replace(temp,mapping)
                            simple[name]='\n'.join(links).encode()
                        body=simple[name];self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
                elif path.startswith('/file/'):
                    _,_,token,filename=path.split('/',3);meta=filename.endswith('.metadata');entry=urls[token]
                    url=entry['url']+('.metadata' if meta else '');expected=None if meta else entry.get('sha256')
                    if entry.get('local_path'):
                        if meta:raise ValueError('Local wheel metadata sidecar unavailable')
                        source=approved_local_wheel(entry)
                    else:source=transfer.get(url,expected=expected)
                    size=source.stat().st_size
                    begin,end=0,size-1;r=self.headers.get('Range')
                    if r:
                        x,y=r.removeprefix('bytes=').split('-');begin=int(x) if x else max(0,size-int(y));end=min(int(y),size-1) if y and x else size-1
                    self.send_response(206 if r else 200);self.send_header('Content-Length',str(end-begin+1));self.send_header('Accept-Ranges','bytes')
                    if r:self.send_header('Content-Range',f'bytes {begin}-{end}/{size}')
                    self.end_headers()
                    with source.open('rb') as f:
                        f.seek(begin);left=end-begin+1
                        while left:
                            b=f.read(min(left,1024*1024));self.wfile.write(b);left-=len(b)
                else:self.send_error(404)
            except (BrokenPipeError,ConnectionResetError):pass
            except BaseException as exc:
                errors.append(type(exc).__name__);print('PROXY_STOP '+type(exc).__name__,flush=True)
                self.send_error(502,type(exc).__name__)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return server,errors
