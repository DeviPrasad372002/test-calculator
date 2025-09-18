import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import pytest

try:
    from fastapi.testclient import TestClient
except ImportError:
    pytest.skip("fastapi.testclient not available", allow_module_level=True)

# Discover a FastAPI app object in likely modules
_app = None
for mod_name in ("app", "main", "target", "SimpleCalculatorPyQt1", "calculator_app"):
    try:
        mod = __import__(mod_name)
        if hasattr(mod, "app"):
            _app = getattr(mod, "app")
            break
    except Exception:
        continue

if _app is None:
    pytest.skip("No FastAPI app object found in common module names", allow_module_level=True)

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (0, 0, 0),
        (1, 2, 3),
        (-5, 7, 2),
        (2.5, 3.5, 6.0),
    ],
)
def test_add_endpoint_basic(a, b, expected):
    
    # Arrange
    client = TestClient(_app)
    payload = {"a": a, "b": b}

    # Act
    resp = client.post("/add", json=payload)

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict)
    assert "result" in body
    result = body["result"]
    assert isinstance(result, (int, float))
    # allow exact equality for integers and floats provided inputs are precise
    assert result == expected

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (5, 3, 2),
        (0, 5, -5),
        (-2, -3, 1),
    ],
)
def test_subtract_endpoint_basic(a, b, expected):
    
    # Arrange
    client = TestClient(_app)
    payload = {"a": a, "b": b}

    # Act
    resp = client.post("/subtract", json=payload)

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert "result" in body
    assert body["result"] == expected

def test_subtract_endpoint_requires_authentication():
    
    # Arrange
    client = TestClient(_app)
    payload = {"a": 10, "b": 1}
    # Act: intentionally omit Authorization header to test permission handling
    resp = client.post("/subtract", json=payload, headers={})

    # Assert: expect explicit 401 Unauthorized when unauthenticated
    assert resp.status_code == 401
    body = resp.json()
    # Expect an error shape with a clear message key
    assert isinstance(body, dict)
    assert "detail" in body or "error" in body
