import hashlib
import io
import pytest
import src.phase25.setup_transfer as transfer
import scripts.phase25d2_setup as setup


class Raw(io.BytesIO):
    def read(self,n=-1,decode_content=False):return super().read(n)


class Response:
    def __init__(self,data=b'abc',length=None,status=200,location=None):
        self.raw=Raw(data);self.headers={'Content-Length':str(length if length is not None else len(data))};self.status_code=status
        if location:self.headers['Location']=location
    def raise_for_status(self):
        if self.status_code>=400:raise RuntimeError('HTTP failure')
    def close(self):pass


class Session:
    def __init__(self,r):self.r=r;self.calls=0
    def get(self,*a,**k):self.calls+=1;return self.r


def test_counted_cache_hash_and_no_duplicate_transfer(tmp_path,monkeypatch):
    monkeypatch.setattr(transfer,'ROOT',tmp_path);t=transfer.Transfers();s=Session(Response());t.session=s
    h=hashlib.sha256(b'abc').hexdigest();p=t.get('https://pypi.org/example',expected=h)
    assert t.get('https://pypi.org/example',expected=h)==p and s.calls==1
    assert t.used('dependency')==16384+3
    p.write_bytes(b'bad')
    with pytest.raises(ValueError):t.get('https://pypi.org/example',expected=h)


def test_budget_stops_before_oversized_body(tmp_path,monkeypatch):
    monkeypatch.setattr(transfer,'ROOT',tmp_path);monkeypatch.setitem(transfer.CAPS,'dependency',32768)
    t=transfer.Transfers();r=Response(length=20000);t.session=Session(r)
    with pytest.raises(RuntimeError,match='cap'):t.get('https://pypi.org/example')
    assert r.raw.tell()==0 and t.used('dependency')<=32768


def test_allowlist_and_redirect_accounting(tmp_path,monkeypatch):
    monkeypatch.setattr(transfer,'ROOT',tmp_path);t=transfer.Transfers();s=Session(Response(status=302,location='https://example.invalid/other'));t.session=s
    with pytest.raises(ValueError):t.get('https://pypi.org/example')
    assert s.calls==1 and t.used('dependency')==16384
    with pytest.raises(ValueError):t.get('http://pypi.org/plain')


def test_low_ram_prevents_any_bootstrap_transfer(monkeypatch):
    def memory(ptr):ptr._obj.available=4*2**30;return True
    monkeypatch.setattr(setup.ctypes.windll.kernel32,'GlobalMemoryStatusEx',memory)
    monkeypatch.setattr(setup,'Transfers',lambda:pytest.fail('Transfer must not start below RAM gate'))
    with pytest.raises(RuntimeError,match='RAM_GATE'):setup.bootstrap312()


def test_existing_venv_only_never_recreated(tmp_path,monkeypatch):
    monkeypatch.setattr(setup,'ENV',tmp_path)
    with pytest.raises(RuntimeError,match='no recreation'):setup.existing_python()
    exe=tmp_path/'Scripts/python.exe';exe.parent.mkdir();exe.write_bytes(b'fixture')
    monkeypatch.setattr(setup.subprocess,'check_output',lambda *a,**k:'Python 3.12.10\n')
    assert setup.existing_python()==exe
    monkeypatch.setattr(setup.subprocess,'check_output',lambda *a,**k:'Python 3.11.8\n')
    with pytest.raises(RuntimeError,match='no substitution'):setup.existing_python()


def test_redirect_cache_reuses_original_verified_identity(tmp_path,monkeypatch):
    monkeypatch.setattr(transfer,'ROOT',tmp_path);t=transfer.Transfers()
    class RedirectSession:
        calls=0
        def get(self,*a,**k):
            self.calls+=1
            return Response(status=302,location='https://files.pythonhosted.org/pkg') if self.calls==1 else Response()
    t.session=RedirectSession();h=hashlib.sha256(b'abc').hexdigest()
    p=t.get('https://pypi.org/pkg',expected=h)
    assert t.get('https://pypi.org/pkg',expected=h)==p and t.session.calls==2


def test_approved_local_wheel_is_hash_bound_and_path_limited(tmp_path,monkeypatch):
    import json
    monkeypatch.setattr(transfer,'ROOT',tmp_path)
    wheel=tmp_path/'antlr4_python3_runtime-4.9.3-py3-none-any.whl'
    wheel.write_bytes(b'audited fixture')
    h=hashlib.sha256(wheel.read_bytes()).hexdigest()
    (tmp_path/'antlr-approved-build.json').write_text(json.dumps(dict(wheel_sha256=h,source_sha256='f224469b4168294902bb1efa80a8bf7855f24c99aef99cbefc1bcd3cce77881b')))
    entry=dict(local_path=str(wheel),sha256=h)
    assert transfer.approved_local_wheel(entry)==wheel
    wheel.write_bytes(b'altered')
    with pytest.raises(ValueError,match='integrity'):transfer.approved_local_wheel(entry)
    entry['local_path']=str(tmp_path/'other.whl')
    with pytest.raises(ValueError,match='Only approved'):transfer.approved_local_wheel(entry)


def test_local_wheel_head_never_fetches_network(tmp_path,monkeypatch):
    import json
    import requests
    monkeypatch.setattr(transfer,'ROOT',tmp_path)
    wheel=tmp_path/'antlr4_python3_runtime-4.9.3-py3-none-any.whl';wheel.write_bytes(b'fixture')
    h=hashlib.sha256(wheel.read_bytes()).hexdigest()
    (tmp_path/'antlr-approved-build.json').write_text(json.dumps(dict(wheel_sha256=h,source_sha256='f224469b4168294902bb1efa80a8bf7855f24c99aef99cbefc1bcd3cce77881b')))
    entry=dict(filename=wheel.name,url='approved-local:antlr4-4.9.3',local_path=str(wheel),sha256=h)
    token=hashlib.sha256(entry['url'].encode()).hexdigest()
    (tmp_path/'source-links.json').write_text(json.dumps({token:entry}))
    t=transfer.Transfers()
    monkeypatch.setattr(t,'get',lambda *a,**k:pytest.fail('No external fetch'))
    server,errors=transfer.serve(t,{},port=0)
    try:
        r=requests.head(f'http://127.0.0.1:{server.server_port}/file/{token}/{wheel.name}',timeout=5)
        assert r.status_code==200 and int(r.headers['Content-Length'])==7 and not r.content
        assert not errors and not t.rows
    finally:server.shutdown();server.server_close()


def test_official_cdn_model_only_and_redirect_hostname_receipt(tmp_path,monkeypatch):
    monkeypatch.setattr(transfer,'ROOT',tmp_path)
    t=transfer.Transfers();t.session=Session(Response())
    with pytest.raises(ValueError,match='Unapproved'):t.get('https://us.aws.cdn.hf.co/checkpoint')
    h=hashlib.sha256(b'abc').hexdigest()
    assert t.get('https://us.aws.cdn.hf.co/checkpoint',kind='model',expected=h).read_bytes()==b'abc'
    assert t.used('model')==16387
    t2=transfer.Transfers();t2.session=Session(Response(status=302,location='https://blocked.invalid/path?secret=never-persist'))
    with pytest.raises(ValueError):t2.get('https://huggingface.co/frozen',kind='model')
    assert t2.rows[-1]['redirect_host']=='blocked.invalid'
    assert 'never-persist' not in t2.path.read_text()


def test_smoke_checkpoint_size_and_hash_fail_closed(tmp_path,monkeypatch):
    import scripts.phase25d2_smoke as smoke
    p=tmp_path/'fake.pt';p.write_bytes(b'abc')
    with pytest.raises(ValueError,match='size'):smoke.verify_checkpoint(p)
    monkeypatch.setattr(smoke,'SIZE',3)
    with pytest.raises(ValueError,match='SHA'):smoke.verify_checkpoint(p)
    monkeypatch.setattr(smoke,'SHA',hashlib.sha256(b'abc').hexdigest())
    smoke.verify_checkpoint(p)


def test_smoke_ram_monitor_includes_windows_launcher_child():
    from types import SimpleNamespace
    from scripts.phase25d2_smoke import process_tree_memory
    class Process:
        def __init__(self,rss,peak,descendants=()):self.info=SimpleNamespace(rss=rss,peak_wset=peak);self.descendants=descendants
        def memory_info(self):return self.info
        def children(self,recursive):assert recursive;return list(self.descendants)
    worker=Process(5*2**30,7*2**30)
    launcher=Process(4*2**20,5*2**20,[worker])
    assert process_tree_memory(launcher)==7*2**30+5*2**20
    assert process_tree_memory(launcher)>6*2**30
