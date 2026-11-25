"""Persistent, bounded HTTP transport for ONE resumable Phase25 pilot."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import httplib2
import requests


class BudgetStop(RuntimeError):
    pass


class MeteredHttp:
    """Count every HTTP attempt (auth/discovery/RPC/download/OSM), no adapter retries.

    Pending attempts retain their full response reservation after interruption.
    Ledger contains no URLs, query strings, credentials, headers or request bodies.
    """
    def __init__(self, ledger, max_requests=60, max_bytes=100_000_000,
                 response_cap=2_000_000, session=None):
        self.path=Path(ledger);self.max_requests=max_requests;self.max_bytes=max_bytes
        self.response_cap=response_cap;self.timeout=120
        self.session=session or requests.Session()
        if session is None:
            for scheme in ('http://','https://'):
                self.session.mount(scheme,requests.adapters.HTTPAdapter(max_retries=0))
        self.rows=[json.loads(x) for x in self.path.read_text().splitlines()] if self.path.exists() else []
        if len(self.rows)>max_requests or self.charged_bytes()>max_bytes:
            raise BudgetStop('Existing ledger exceeds frozen budget')

    def charged_bytes(self):
        return sum(r['reserved_bytes'] if r['state']=='PENDING' else r['response_bytes'] for r in self.rows)

    def persist(self):
        tmp=self.path.with_suffix('.pending')
        tmp.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in self.rows),encoding='utf-8')
        os.replace(tmp,self.path)

    def request(self, uri, method='GET', body=None, headers=None, **kwargs):
        u=urlsplit(uri)
        if u.scheme!='https' or u.hostname not in {'earthengine.googleapis.com','oauth2.googleapis.com',
                'accounts.google.com','www.googleapis.com','storage.googleapis.com','overpass-api.de'}:
            raise ValueError('Unapproved transport endpoint; no request sent')
        if len(self.rows)>=self.max_requests or self.charged_bytes()+self.response_cap>self.max_bytes:
            raise BudgetStop('Stop BEFORE request/byte cap')
        row=dict(attempt=len(self.rows)+1,host=u.hostname,state='PENDING',reserved_bytes=self.response_cap,response_bytes=0)
        self.rows.append(row);self.persist()
        response=None;chunks=[];received=0
        try:
            h=dict(headers or {});h['Accept-Encoding']='identity'
            response=self.session.request(method,uri,data=body,headers=h,stream=True,
                                          allow_redirects=False,timeout=(20,self.timeout))
            row['http_status']=int(response.status_code)
            length=response.headers.get('Content-Length')
            if length is not None and int(length)>self.response_cap:
                raise BudgetStop('Response exceeds preregistered per-response cap; body not read')
            if response.headers.get('Content-Encoding','identity') not in ('identity',''):
                raise BudgetStop('Unexpected compression; refuse unbounded decoding')
            while True:
                left=self.response_cap-received
                if left==0:
                    if length is not None and received==int(length):break
                    raise BudgetStop('Stop BEFORE reading beyond response cap')
                part=response.raw.read(min(65536,left),decode_content=False)
                if not part:break
                received+=len(part);chunks.append(part)
            if length is not None and received!=int(length):raise RuntimeError('Truncated response')
            row.update(state='COMPLETE',response_bytes=received)
            self.persist()
            hdr={k.lower():v for k,v in response.headers.items()};hdr['status']=str(response.status_code)
            return httplib2.Response(hdr),b''.join(chunks)
        except BaseException as exc:
            row.update(state='FAILED',response_bytes=received,error=type(exc).__name__)
            self.persist();raise
        finally:
            if response is not None:response.close()

    def summary(self):
        return dict(requests=len(self.rows),received_response_body_bytes=sum(r['response_bytes'] for r in self.rows),
                    charged_bytes_including_pending=self.charged_bytes(),pending=sum(r['state']=='PENDING' for r in self.rows),
                    request_cap=self.max_requests,byte_cap=self.max_bytes)
