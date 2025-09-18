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

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
import time

try:
    import pytest
    import requests
    from target.Calculator import Calculator, CalculatorError
    from target.SimpleCalculatorPyQt1 import clear_history, clear_input
except Exception as e:
    import pytest as _pytest
    _pytest.skip("Skipping HTTP E2E tests due to missing imports: %s" % e, allow_module_level=True)

def _start_test_server(handler_cls):
    # bind to an ephemeral port
    server = HTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port, thread

class CalcHandler(BaseHTTPRequestHandler):
    # Shared calculator instance across requests to simulate stateful history if any
    calc = Calculator()

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            if self.path == "/calculate":
                data = self._read_json()
                op = data.get("op")
                a = data.get("a")
                b = data.get("b")
                # Basic input validation
                if op not in ("add", "subtract", "multiply", "divide"):
                    return self._send_json(400, {"error": "unsupported_operation", "op": op})
                if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                    return self._send_json(400, {"error": "invalid_operands"})
                try:
                    if op == "add":
                        result = self.calc.add(a, b)
                    elif op == "subtract":
                        result = self.calc.subtract(a, b)
                    elif op == "multiply":
                        result = self.calc.multiply(a, b)
                    else:
                        result = self.calc.divide(a, b)
                    return self._send_json(200, {"op": op, "a": a, "b": b, "result": result})
                except CalculatorError as ce:
                    return self._send_json(400, {"error": "calculator_error", "message": str(ce)})
            elif self.path == "/clear_history":
                # permission required: header Authorization: Token secret-token
                auth = self.headers.get("Authorization", "")
                if auth != "Token secret-token":
                    return self._send_json(403, {"error": "forbidden", "required": "Token secret-token"})
                # call module-level clear_history (imported in test module)
                try:
                    clear_history()
                except Exception as e:
                    return self._send_json(500, {"error": "clear_failed", "message": str(e)})
                return self._send_json(200, {"cleared": True})
            elif self.path == "/clear_input":
                # no permission required
                try:
                    clear_input()
                except Exception as e:
                    return self._send_json(500, {"error": "clear_input_failed", "message": str(e)})
                return self._send_json(200, {"cleared": True})
            else:
                return self._send_json(404, {"error": "not_found"})
        except Exception as exc:
            self._send_json(500, {"error": "internal", "message": str(exc)})

    def log_message(self, format, *args):
        # suppress logging to stderr during tests
        return

def _shutdown_server(server, thread):
    if server:
        server.shutdown()
        server.server_close()
    if thread and thread.is_alive():
        thread.join(timeout=1)

def _wait_for_server(port, timeout=1.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"http://127.0.0.1:{port}/nonexistent", timeout=0.2)
        except requests.RequestException:
            time.sleep(0.01)
            continue
        return
    raise RuntimeError("Server did not start in time")

def test_calculate_add_success():
    
    # Arrange
    server, port, thread = _start_test_server(CalcHandler)
    try:
        _wait_for_server(port)
        url = f"http://127.0.0.1:{port}/calculate"
        payload = {"op": "add", "a": 7, "b": 5}

        # Act
        resp = requests.post(url, json=payload, timeout=2.0)

        # Assert
        assert resp.status_code == 200
        j = resp.json()
        assert set(j.keys()) == {"op", "a", "b", "result"}
        assert j["op"] == "add"
        assert isinstance(j["result"], (int, float))
        assert j["result"] == 12
        assert j["a"] == 7 and j["b"] == 5
    finally:
        _shutdown_server(server, thread)

def test_calculate_divide_by_zero_returns_calculator_error():
    
    # Arrange
    server, port, thread = _start_test_server(CalcHandler)
    try:
        _wait_for_server(port)
        url = f"http://127.0.0.1:{port}/calculate"
        payload = {"op": "divide", "a": 10, "b": 0}

        # Act
        resp = requests.post(url, json=payload, timeout=2.0)

        # Assert
        assert resp.status_code == 400
        j = resp.json()
        assert "error" in j and j["error"] == "calculator_error"
        assert "message" in j and isinstance(j["message"], str)
    finally:
        _shutdown_server(server, thread)

def test_clear_history_requires_authorization_and_succeeds_with_token():
    
    # Arrange
    server, port, thread = _start_test_server(CalcHandler)
    try:
        _wait_for_server(port)
        url = f"http://127.0.0.1:{port}/clear_history"

        # Act - missing token should be forbidden
        resp_no_auth = requests.post(url, json={}, timeout=2.0)

        # Assert - negative permission case
        assert resp_no_auth.status_code == 403
        j_no = resp_no_auth.json()
        assert j_no.get("error") == "forbidden"
        assert j_no.get("required") == "Token secret-token"

        # Act - with correct token should succeed
        headers = {"Authorization": "Token secret-token"}
        resp_auth = requests.post(url, json={}, headers=headers, timeout=2.0)

        # Assert - success case
        assert resp_auth.status_code == 200
        j_yes = resp_auth.json()
        assert j_yes == {"cleared": True}
    finally:
        _shutdown_server(server, thread)
