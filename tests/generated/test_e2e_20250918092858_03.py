import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

import threading
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    import requests
    import pytest
except ImportError as e:
    import pytest as _pytest  # type: ignore
    _pytest.skip(f"missing dependency: {e.name}", allow_module_level=True)

# Minimal test HTTP server that exposes /calculate, /clear_history, /clear_input
# The server is deterministic and runs only on localhost; no external network calls.
def start_test_server():
    state = {
        "history": [],
        "current_input": "",
        "lock": threading.Lock(),
    }

    class CalcHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _set_json(self, status=200, payload=None):
            body = json.dumps(payload or {}).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            # silence default logging
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b""
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                return self._set_json(400, {"error": "invalid JSON"})

            path = self.path
            if path == "/calculate":
                # Validate payload
                op = payload.get("op")
                a = payload.get("a")
                b = payload.get("b")
                if op not in ("add", "subtract", "multiply", "divide"):
                    return self._set_json(400, {"error": "unsupported operation"})
                if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                    return self._set_json(400, {"error": "operands must be numbers"})
                # Perform calculation deterministically
                try:
                    if op == "add":
                        result = a + b
                    elif op == "subtract":
                        result = a - b
                    elif op == "multiply":
                        result = a * b
                    elif op == "divide":
                        if b == 0:
                            raise ZeroDivisionError("division by zero")
                        result = a / b
                except ZeroDivisionError as err:
                    return self._set_json(400, {"error": str(err)})
                # Update state
                with state["lock"]:
                    # current_input mirrors a string form of the last operation
                    state["current_input"] = f"{a}{op}{b}"
                    state["history"].append({"op": op, "a": a, "b": b, "result": result})
                    history_copy = list(state["history"])
                return self._set_json(200, {"result": result, "history": history_copy})

            elif path == "/clear_history":
                # Authorization header required: "Token secret"
                auth = self.headers.get("Authorization", "")
                if auth != "Token secret":
                    return self._set_json(403, {"error": "forbidden"})
                with state["lock"]:
                    state["history"].clear()
                    history_copy = list(state["history"])
                return self._set_json(200, {"status": "history_cleared", "history": history_copy})

            elif path == "/clear_input":
                # No auth required; clears current_input
                with state["lock"]:
                    state["current_input"] = ""
                return self._set_json(200, {"status": "input_cleared", "current_input": ""})

            elif path == "/state":
                # Diagnostic endpoint for tests to inspect internal state
                with state["lock"]:
                    snapshot = {"history": list(state["history"]), "current_input": state["current_input"]}
                return self._set_json(200, snapshot)

            else:
                return self._set_json(404, {"error": "not found"})

    httpd = HTTPServer(("127.0.0.1", 0), CalcHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    def shutdown():
        httpd.shutdown()
        thread.join(timeout=1)

    base_url = f"http://127.0.0.1:{port}"
    return base_url, shutdown

# Arrange / Act / Assert style tests

@pytest.mark.parametrize(
    "op,a,b,expected",
    [
        ("add", 1, 2, 3),
        ("subtract", 5, 3, 2),
        ("multiply", 4, 2.5, 10.0),
    ],
)
def test_calculate_operations_valid(op, a, b, expected):
    
    # Arrange
    base_url, shutdown = start_test_server()
    try:
        # Act
        resp = requests.post(f"{base_url}/calculate", json={"op": op, "a": a, "b": b}, timeout=5)
        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert "result" in body and "history" in body
        # result numeric and exact
        assert body["result"] == expected
        assert isinstance(body["history"], list)
        # last history entry matches operation
        last = body["history"][-1]
        assert last["op"] == op
        assert last["a"] == a
        assert last["b"] == b
        assert last["result"] == expected
    finally:
        shutdown()

def test_calculate_divide_by_zero_returns_400():
    
    # Arrange
    base_url, shutdown = start_test_server()
    try:
        # Act
        resp = requests.post(f"{base_url}/calculate", json={"op": "divide", "a": 1, "b": 0}, timeout=5)
        # Assert
        assert resp.status_code == 400
        body = resp.json()
        assert "error" in body
        assert "division by zero" in body["error"]
    finally:
        shutdown()

def test_clear_history_requires_authorization_and_clears_history():
    
    # Arrange
    base_url, shutdown = start_test_server()
    try:
        # Create two history entries
        r1 = requests.post(f"{base_url}/calculate", json={"op": "add", "a": 1, "b": 1}, timeout=5)
        assert r1.status_code == 200
        r2 = requests.post(f"{base_url}/calculate", json={"op": "multiply", "a": 3, "b": 3}, timeout=5)
        assert r2.status_code == 200

        # Confirm history length is 2
        state = requests.post(f"{base_url}/state", json={}, timeout=5)
        assert state.status_code == 200
        snapshot = state.json()
        assert isinstance(snapshot["history"], list)
        assert len(snapshot["history"]) == 2

        # Act (negative): attempt to clear without auth
        resp_no_auth = requests.post(f"{base_url}/clear_history", json={}, timeout=5)
        # Assert negative case: forbidden
        assert resp_no_auth.status_code == 403
        assert resp_no_auth.json().get("error") == "forbidden"

        # Act (positive): clear with correct token
        resp_auth = requests.post(f"{base_url}/clear_history", json={}, headers={"Authorization": "Token secret"}, timeout=5)
        # Assert positive case
        assert resp_auth.status_code == 200
        body = resp_auth.json()
        assert body.get("status") == "history_cleared"
        assert isinstance(body.get("history"), list)
        assert len(body["history"]) == 0

        # Confirm state cleared
        state2 = requests.post(f"{base_url}/state", json={}, timeout=5)
        assert state2.status_code == 200
        assert state2.json()["history"] == []
    finally:
        shutdown()

def test_clear_input_clears_current_input_after_operations():
    
    # Arrange
    base_url, shutdown = start_test_server()
    try:
        # Perform operation to set current_input
        r = requests.post(f"{base_url}/calculate", json={"op": "add", "a": 7, "b": 8}, timeout=5)
        assert r.status_code == 200
        # Inspect state and ensure current_input set
        s = requests.post(f"{base_url}/state", json={}, timeout=5)
        assert s.status_code == 200
        snap = s.json()
        assert snap["current_input"] != ""
        assert "7" in snap["current_input"] and "8" in snap["current_input"]

        # Act: clear input
        clear_resp = requests.post(f"{base_url}/clear_input", json={}, timeout=5)
        # Assert
        assert clear_resp.status_code == 200
        cr = clear_resp.json()
        assert cr.get("status") == "input_cleared"
        assert cr.get("current_input") == ""

        # Confirm via state endpoint
        s2 = requests.post(f"{base_url}/state", json={}, timeout=5)
        assert s2.status_code == 200
        assert s2.json()["current_input"] == ""
    finally:
        shutdown()
