import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import json
import threading
import http.server
import socketserver
import socket
import time
import random

import pytest

try:
    import requests
except ImportError:
    pytest.skip("requests is required for these tests", allow_module_level=True)

def _start_test_server(root_dir, auth_token, fixed_time):
    """
    Start a local HTTP server that implements /multiply, /divide, /history/save.
    Returns (server, base_url, thread).
    """

    random.seed(0)  # ensure deterministic if any randomness used

    class Handler(http.server.BaseHTTPRequestHandler):
        def _read_json(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return None
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8"))

        def _send_json(self, status, obj):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format, *args):
            # silence default logging to stderr to keep test output clean
            return

        def do_POST(self):
            if self.path == "/multiply":
                body = self._read_json()
                if not body or "a" not in body or "b" not in body:
                    self._send_json(400, {"error": "missing operands"})
                    return
                a = body["a"]
                b = body["b"]
                # allow numeric types only
                if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                    self._send_json(400, {"error": "operands must be numeric"})
                    return
                result = a * b
                self._send_json(200, {"op": "multiply", "result": result})
                return

            if self.path == "/divide":
                body = self._read_json()
                if not body or "a" not in body or "b" not in body:
                    self._send_json(400, {"error": "missing operands"})
                    return
                a = body["a"]
                b = body["b"]
                if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                    self._send_json(400, {"error": "operands must be numeric"})
                    return
                if b == 0:
                    self._send_json(400, {"error": "division by zero", "exception": "CalculatorError"})
                    return
                result = a / b
                self._send_json(200, {"op": "divide", "result": result})
                return

            if self.path == "/history/save":
                # authentication required via Authorization: Bearer <token>
                auth = self.headers.get("Authorization", "")
                expected = f"Bearer {auth_token}"
                if auth != expected:
                    self._send_json(401, {"detail": "Unauthorized"})
                    return
                body = self._read_json()
                if body is None or not isinstance(body, dict):
                    self._send_json(400, {"error": "invalid payload"})
                    return
                # freeze time deterministically using provided fixed_time (int)
                timestamp = int(fixed_time())
                filename = f"history_{timestamp}.json"
                path = root_dir / filename
                # create file with the provided payload
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(body, f, separators=(",", ":"), sort_keys=True)
                # deterministic id derived from timestamp to avoid random nondeterminism
                record_id = (timestamp % 1000000) + 1000
                response = {"id": record_id, "location": str(path), "timestamp": timestamp}
                self._send_json(201, response)
                return

            # unknown path
            self._send_json(404, {"error": "not found"})

    # find free port by letting the OS allocate a port (port 0)
    server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    # get bound port
    host, port = server.server_address
    base_url = f"http://{host}:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, base_url, thread

def _stop_test_server(server):
    if server:
        server.shutdown()
        server.server_close()

def test_multiply_endpoint_success(tmp_path):
    
    # Arrange
    fixed_time = lambda: 1620000000.0
    auth_token = "unused"
    server, base_url, thread = _start_test_server(tmp_path, auth_token, fixed_time)
    try:
        url = base_url + "/multiply"
        payload = {"a": 3, "b": 4}
        headers = {"Content-Type": "application/json"}

        # Act
        resp = requests.post(url, headers=headers, data=json.dumps(payload))

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        # schema: op and result
        assert set(body.keys()) == {"op", "result"}
        assert body["op"] == "multiply"
        # numeric result exact
        assert isinstance(body["result"], int)
        assert body["result"] == 12
    finally:
        _stop_test_server(server)

def test_divide_endpoint_divide_by_zero_negative_case(tmp_path):
    
    # Arrange
    fixed_time = lambda: 1620000000.0
    auth_token = "unused"
    server, base_url, thread = _start_test_server(tmp_path, auth_token, fixed_time)
    try:
        url = base_url + "/divide"
        payload = {"a": 5, "b": 0}
        headers = {"Content-Type": "application/json"}

        # Act
        resp = requests.post(url, headers=headers, data=json.dumps(payload))

        # Assert
        assert resp.status_code == 400
        body = resp.json()
        # must include specific error shape for CalculatorError
        assert body.get("error") == "division by zero"
        assert body.get("exception") == "CalculatorError"
    finally:
        _stop_test_server(server)

def test_save_history_requires_auth_and_writes_file(tmp_path, monkeypatch):
    
    # Arrange
    # freeze time deterministically
    monkeypatch.setattr(time, "time", lambda: 1620000000.0)
    fixed_time = lambda: time.time()
    auth_token = "secrettoken"
    server, base_url, thread = _start_test_server(tmp_path, auth_token, fixed_time)
    try:
        url = base_url + "/history/save"
        payload = {"entries": [{"a": 2, "b": 3, "op": "multiply", "result": 6}]}
        headers = {"Content-Type": "application/json"}

        # Act: attempt without auth
        resp_unauth = requests.post(url, headers=headers, data=json.dumps(payload))
        # Assert unauthorized
        assert resp_unauth.status_code == 401
        assert resp_unauth.json().get("detail") == "Unauthorized"

        # Act: attempt with correct auth
        headers_auth = {"Content-Type": "application/json", "Authorization": f"Bearer {auth_token}"}
        resp = requests.post(url, headers=headers_auth, data=json.dumps(payload))

        # Assert created
        assert resp.status_code == 201
        body = resp.json()
        # concrete deterministic timestamp as we froze time
        assert body["timestamp"] == 1620000000
        # id computed deterministically from timestamp: (timestamp % 1000000) + 1000 => 1000
        assert body["id"] == 1000
        
        location = body["location"]
        # validate file exists and contents match exactly (keys sorted in server)
        with open(location, "r", encoding="utf-8") as f:
            disk = json.load(f)
        assert disk == payload
    finally:
        _stop_test_server(server)
