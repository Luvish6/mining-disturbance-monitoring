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
