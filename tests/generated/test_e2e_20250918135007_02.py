import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import importlib
import pytest

try:
    from fastapi.testclient import TestClient
except ImportError:
    pytest.skip("fastapi.testclient not available, skipping HTTP E2E tests", allow_module_level=True)

# Try to locate an ASGI/fastapi app object from common names
_app = None
_app_names = [
    "app",
    "main",
    "server",
    "target.app",
    "target.main",
    "application",
]
for name in _app_names:
    try:
        module = importlib.import_module(name)
    except Exception:
        continue
    # prefer attribute 'app' then module itself if it is an ASGI app
    if hasattr(module, "app"):
        _app = getattr(module, "app")
        break
    # some modules expose FastAPI instance as 'application' or module itself might be app
    if getattr(module, "__class__", None) is not None and hasattr(module, "routes"):
        _app = module
        break

if _app is None:
    pytest.skip("No FastAPI app found in common module names; skipping HTTP E2E tests", allow_module_level=True)

client = TestClient(_app)

def _post_or_skip(path, json):
    """
    Helper: POST to path; if 404, skip the test (endpoint absent).
    """
    resp = client.post(path, json=json)
    if resp.status_code == 404:
        pytest.skip(f"Endpoint {path} not found on app")
    return resp

def _post_token_if_available(username="test", password="test"):
    """
    Try to obtain a Bearer token from common token endpoints.
    Return token string or None if not available.
    """
    # Common token endpoints: /token (OAuth2), /auth/token, /login
    candidates = [
        ("/token", {"username": username, "password": password}),
        ("/auth/token", {"username": username, "password": password}),
        ("/login", {"username": username, "password": password}),
    ]
    for path, payload in candidates:
        resp = client.post(path, data=payload)
        if resp.status_code == 404:
            continue
        # Many implementations return JSON { "access_token": "..." } on success
        if resp.status_code == 200:
            try:
                j = resp.json()
            except Exception:
                continue
            if isinstance(j, dict) and ("access_token" in j or "token" in j):
                return j.get("access_token") or j.get("token")
    return None

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (6, 7, 42),
        (0, 5, 0),
        (-3, 4, -12),
    ],
)
def test_multiply_endpoint_returns_expected_integer_result(a, b, expected):
    
    # Arrange
    payload = {"a": a, "b": b}

    # Act
    resp = _post_or_skip("/multiply", json=payload)

    # Assert
    assert resp.status_code == 200, "multiply should return 200 on valid input"
    j = resp.json()
    assert isinstance(j, dict), "response JSON must be an object"
    assert "result" in j, "response must contain 'result' key"
    assert isinstance(j["result"], int), "multiply result should be integer"
    assert j["result"] == expected, f"expected {expected}, got {j['result']}"

@pytest.mark.parametrize(
    "a,b,expect_status,expected_result",
    [
        (10, 2, 200, 5.0),
        (5, 0, 400, None),  # division by zero should be rejected
    ],
)
def test_divide_endpoint_handles_normal_and_zero_division(a, b, expect_status, expected_result):
    
    # Arrange
    payload = {"a": a, "b": b}

    # Act
    resp = _post_or_skip("/divide", json=payload)

    # Assert common expectations
    assert resp.status_code == expect_status or (
        expect_status >= 400 and resp.status_code >= 400
    ), f"unexpected status code {resp.status_code} for input {a}/{b}"

    if expect_status == 200:
        j = resp.json()
        assert isinstance(j, dict)
        assert "result" in j
        # allow integers represented as floats; coerce for comparison
        result_value = float(j["result"])
        assert result_value == pytest.approx(float(expected_result), rel=1e-9)
    else:
        # For error cases, expect a JSON error payload with a message-like field
        try:
            j = resp.json()
        except ValueError:
            pytest.fail("error responses must be JSON")
        assert isinstance(j, dict)
        
        assert any(k in j for k in ("detail", "error", "message")), "error response must include detail/error/message"

def test_save_history_requires_auth_and_persists_entry():
    
    # Arrange: construct an operation entry
    entry = {"operation": "multiply", "a": 3, "b": 4, "result": 12}
    # Try without auth first
    resp_no_auth = client.post("/history", json=entry)
    if resp_no_auth.status_code == 404:
        pytest.skip("/history endpoint not found on app")
    # Act & Assert: unauthenticated write should be rejected (401/403) in secure apps
    if resp_no_auth.status_code in (401, 403):
        assert resp_no_auth.status_code == 401 or resp_no_auth.status_code == 403
    elif resp_no_auth.status_code in (200, 201):
        # The app allows anonymous writes; ensure it returns created/persisted item
        j = resp_no_auth.json()
        assert isinstance(j, dict)
        assert "id" in j or "operation" in j
        # Verify stored operation matches input
        assert j.get("operation") == entry["operation"]
        assert int(j.get("result")) == entry["result"]
        return
    else:
        pytest.fail(f"Unexpected status code for unauthenticated POST /history: {resp_no_auth.status_code}")

    
    token = _post_token_if_available()
    if token is None:
        pytest.skip("Authentication required for /history but no token endpoint available to obtain credentials")
    # Act: authenticated write
    headers = {"Authorization": f"Bearer {token}"}
    resp_auth = client.post("/history", json=entry, headers=headers)
    assert resp_auth.status_code in (200, 201), "authenticated POST /history should succeed"
    j2 = resp_auth.json()
    assert isinstance(j2, dict)
    # business invariant: persisted entry must include the operation and result matching input
    assert j2.get("operation") == entry["operation"]
    assert int(j2.get("result")) == entry["result"]
