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
import time

# Guard imports for web frameworks; skip entire module if none found.
try:
    from fastapi.testclient import TestClient  # type: ignore
    framework = "fastapi"
except Exception:
    try:
        from rest_framework.test import APIClient  # type: ignore
        framework = "drf"
    except Exception:
        pytest.skip("No FastAPI or Django REST framework detected; skipping HTTP E2E tests.", allow_module_level=True)

# Attempt to locate an ASGI/FastAPI app or a Django REST entrypoint in several common locations.
app_obj = None
if framework == "fastapi":
    candidate_modules = ["target.app", "app", "main", "target.main", "server", "target.server"]
    for mod_name in candidate_modules:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        # common attribute names
        for attr in ("app", "application", "fastapi_app"):
            app_obj = getattr(mod, attr, None)
            if app_obj is not None:
                break
        if app_obj is not None:
            break
    if app_obj is None:
        pytest.skip("FastAPI detected but no application object found in common modules; skipping HTTP E2E tests.", allow_module_level=True)
    client = TestClient(app_obj)
else:
    
    
    candidate_modules = ["target.urls", "urls", "project.urls"]
    django_urls = None
    for mod_name in candidate_modules:
        try:
            django_urls = importlib.import_module(mod_name)
            break
        except Exception:
            continue
    if django_urls is None:
        pytest.skip("Django REST framework detected but no URLConf found in common locations; skipping HTTP E2E tests.", allow_module_level=True)
    # Use APIClient to hit endpoints; it will attempt local test server behavior.
    client = APIClient()

# Freeze time for deterministic behavior where server uses time.time()
_fixed_time = 1609459200.0  # 2021-01-01T00:00:00Z

@pytest.fixture(autouse=True)
def freeze_time(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: _fixed_time)
    yield

@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"a": 2, "b": 3, "op": "add"}, 5),
        ({"a": 10, "b": 4, "op": "subtract"}, 6),
    ],
)
def test_calculate_add_subtract_end_to_end(payload, expected):
    
    # Arrange
    url = "/calculate"
    # Act
    response = client.post(url, json=payload)
    
    if response.status_code in (404, 405):
        pytest.skip(f"Endpoint {url} not available or method not allowed; skipping test.")
    # Assert
    assert response.status_code == 200, f"Unexpected status code: {response.status_code} body: {response.text}"
    data = response.json()
    assert isinstance(data, dict), "Response JSON must be an object"
    assert "result" in data, "Response JSON must contain 'result' key"
    assert data["result"] == expected, f"Expected result {expected}, got {data['result']}"

@pytest.mark.parametrize(
    "endpoint,body,expected_status",
    [
        ("/add", {"x": 7, "y": 5}, 200),
        ("/subtract", {"x": 9, "y": 2}, 200),
    ],
)
def test_alternate_endpoints_support_basic_ops(endpoint, body, expected_status):
    
    # Arrange
    # Act
    response = client.post(endpoint, json=body)
    # Skip if endpoint does not exist on this app instance
    if response.status_code in (404, 405):
        pytest.skip(f"Endpoint {endpoint} not implemented on this application; skipping.")
    # Assert
    assert response.status_code == expected_status, f"Unexpected status code for {endpoint}"
    data = response.json()
    assert isinstance(data, dict), "Response JSON must be a dict"
    assert "result" in data and isinstance(data["result"], (int, float)), "Result must be numeric"

def test_history_permission_negative_case():
    
    # Arrange
    url = "/history"
    # Act
    response = client.get(url)
    # If endpoint not present, skip
    if response.status_code in (404, 405):
        pytest.skip(f"Endpoint {url} not present; skipping permission negative test.")
    # Assert: Prefer explicit unauthorized response; allow 401 or 403 as correct negative/permission behavior.
    if response.status_code in (401, 403):
        assert response.status_code in (401, 403)
    else:
        # If the endpoint returns 200, assert that the returned structure is well-formed and does not leak sensitive data.
        assert response.status_code == 200, f"Unexpected status code for {url}: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "History endpoint must return a list when accessible"
        
        if data:
            entry = data[0]
            assert isinstance(entry, dict), "History item must be an object"
            assert "operation" in entry or "op" in entry, "History items must include an operation description"
            # If timestamps are provided, they should be numeric and not in the future relative to frozen time
            if "timestamp" in entry:
                ts = entry["timestamp"]
                assert isinstance(ts, (int, float)), "timestamp must be numeric"
                assert ts <= _fixed_time, "timestamp must not be in the future"
