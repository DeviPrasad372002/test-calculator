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
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

# Guard third-party imports
try:
    import requests
except ImportError:
    pytest.skip("requests is required for these E2E HTTP tests", allow_module_level=True)

# Guard importing the target Calculator implementation
try:
    from target.Calculator import Calculator, CalculatorError
except Exception:
    pytest.skip("target.Calculator not importable; skipping HTTP E2E tests", allow_module_level=True)

def _start_local_calc_server(monkeypatch, fixed_time=1600000000.0):
    """
    Start a minimal local HTTP server that wraps the Calculator class.
    Returns (base_url, shutdown_callable).
    """
    # Freeze time for deterministic timestamps inside history entries if used
    import time
    original_time = time.time
    monkeypatch.setattr(time, "time", lambda: fixed_time)

    calculator = Calculator()

    class CalcHandler(BaseHTTPRequestHandler):
        # suppress logging
        def log_message(self, format, *args):
            return

        def _respond(self, status, obj):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b""
            try:
                payload = json.loads(body.decode("utf-8")) if body else {}
            except Exception:
                self._respond(400, {"error": "invalid_json"})
                return

            if self.path == "/calculate":
                # Expect keys: op, a, b
                op = payload.get("op")
                a = payload.get("a")
                b = payload.get("b")
                if op not in ("add", "subtract", "multiply", "divide"):
                    self._respond(400, {"error": "unsupported_operation"})
                    return
                try:
                    if op == "add":
                        result = calculator.add(a, b)
                    elif op == "subtract":
                        result = calculator.subtract(a, b)
                    elif op == "multiply":
                        result = calculator.multiply(a, b)
                    else:
                        result = calculator.divide(a, b)
                except Exception as e:
                    # surface CalculatorError specially
                    if isinstance(e, CalculatorError):
                        self._respond(400, {"error": "calculator_error", "message": str(e), "type": e.__class__.__name__})
                        return
                    self._respond(500, {"error": "internal_error", "message": str(e)})
                    return
                self._respond(200, {"result": result, "operation": op})
                return

            if self.path == "/clear_history":
                calculator.clear_history()
                self._respond(200, {"cleared": True})
                return

            self._respond(404, {"error": "not_found"})

        def do_GET(self):
            if self.path == "/history":
                # Return history as JSON list
                hist = getattr(calculator, "history", [])
                # Ensure serializable
                safe_hist = []
                for entry in hist:
                    safe_hist.append(entry)
                self._respond(200, {"history": safe_hist})
                return
            self._respond(404, {"error": "not_found"})

    # Bind to an ephemeral port
    server = HTTPServer(("127.0.0.1", 0), CalcHandler)
    # store server-side state if needed
    server.calculator = calculator

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address
    base_url = f"http://{host}:{port}"

    def shutdown():
        try:
            server.shutdown()
            server.server_close()
        finally:
            # restore original time
            monkeypatch.setattr(time, "time", original_time)

    return base_url, shutdown

def _post_json(url, payload):
    return requests.post(url, json=payload, timeout=5)

def _get_json(url):
    return requests.get(url, timeout=5)

def test_calculate_add_success(monkeypatch):
    
    # Arrange
    base_url, shutdown = _start_local_calc_server(monkeypatch, fixed_time=1600000000.0)
    try:
        url = f"{base_url}/calculate"
        payload = {"op": "add", "a": 3, "b": 4}

        # Act
        resp = _post_json(url, payload)

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "result" in data and "operation" in data
        assert data["operation"] == "add"
        assert data["result"] == 7
    finally:
        shutdown()

def test_calculate_divide_by_zero_error(monkeypatch):
    
    # Arrange
    base_url, shutdown = _start_local_calc_server(monkeypatch, fixed_time=1600000000.0)
    try:
        url = f"{base_url}/calculate"
        payload = {"op": "divide", "a": 10, "b": 0}

        # Act
        resp = _post_json(url, payload)

        # Assert: Calculator should return a 400 with CalculatorError info
        assert resp.status_code == 400
        data = resp.json()
        assert isinstance(data, dict)
        assert data.get("error") == "calculator_error"
        # message and type provide concrete info
        assert "message" in data and isinstance(data["message"], str)
        assert data.get("type") == "CalculatorError"

        
        hist_resp = _get_json(f"{base_url}/history")
        assert hist_resp.status_code == 200
        hist = hist_resp.json().get("history")
        assert isinstance(hist, list)
        assert len(hist) == 0
    finally:
        shutdown()

def test_history_persistence_and_clear(monkeypatch):
    
    # Arrange
    base_url, shutdown = _start_local_calc_server(monkeypatch, fixed_time=1600000000.0)
    try:
        calc_url = f"{base_url}/calculate"
        history_url = f"{base_url}/history"
        clear_url = f"{base_url}/clear_history"

        # Act: perform several operations
        r1 = _post_json(calc_url, {"op": "add", "a": 1, "b": 2})
        r2 = _post_json(calc_url, {"op": "multiply", "a": 5, "b": 6})
        r3 = _post_json(calc_url, {"op": "subtract", "a": 10, "b": 3})

        # Assert responses succeeded
        assert r1.status_code == 200 and r1.json()["result"] == 3
        assert r2.status_code == 200 and r2.json()["result"] == 30
        assert r3.status_code == 200 and r3.json()["result"] == 7

        # Act: fetch history
        hist_resp = _get_json(history_url)
        assert hist_resp.status_code == 200
        hist = hist_resp.json().get("history")
        assert isinstance(hist, list)

        
        results = [entry.get("result") if isinstance(entry, dict) else None for entry in hist]
        assert results == [3, 30, 7]

        # Act: clear history
        clear_resp = requests.post(clear_url, timeout=5)
        assert clear_resp.status_code == 200
        assert clear_resp.json().get("cleared") is True

        # Assert: history is empty afterwards
        hist_after = _get_json(history_url)
        assert hist_after.status_code == 200
        assert hist_after.json().get("history") == []
    finally:
        shutdown()
