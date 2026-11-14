from http.client import HTTPConnection
from threading import Thread

from scripts.phase8_planet_portal import PREFIX, ThreadingHTTPServer, handler


def test_private_routes_require_numeric_loopback_host_and_same_origin(tmp_path):
    (tmp_path / "index.html").write_text("portal")
    files = {"receipt.json": ("application/json", b"{}")}
    with ThreadingHTTPServer(("127.0.0.1", 0), handler(tmp_path, files, "127.0.0.1")) as server:
        worker = Thread(target=server.serve_forever)
        worker.start()
        try:
            def get(path, **headers):
                connection = HTTPConnection("127.0.0.1", server.server_port)
                connection.request("GET", path, headers={"Host": "127.0.0.1", **headers})
                response = connection.getresponse()
                result = response.status, response.getheader("Cache-Control"), response.read()
                connection.close()
                return result

            same_origin = {"Sec-Fetch-Site": "same-origin"}
            assert get("/")[2] == b"portal"
            assert get(PREFIX + "receipt.json")[0] == 403
            assert get(PREFIX + "receipt.json", Host="example.invalid", **same_origin)[0] == 403
            assert get(PREFIX + "receipt.json", Origin="https://example.invalid", **same_origin)[0] == 403
            assert get(PREFIX + "receipt.json", **same_origin) == (200, "no-store", b"{}")
            assert get(PREFIX + "missing.png", **same_origin)[0] == 404
            assert get("/../AGENTS.md", **same_origin)[0] == 404
        finally:
            server.shutdown()
            worker.join()
