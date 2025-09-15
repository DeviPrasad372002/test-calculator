
# --- ENHANCED UNIVERSAL BOOTSTRAP ---
import os, sys, importlib.util as _iu, types as _types, pytest as _pytest, builtins as _builtins, warnings
STRICT = os.getenv("TESTGEN_STRICT", "1").lower() in ("1","true","yes")
STRICT_FAIL = os.getenv("TESTGEN_STRICT_FAIL","0").lower() in ("1","true","yes")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

_target = os.environ.get("TARGET_ROOT") or os.environ.get("ANALYZE_ROOT")
if _target and os.path.isdir(_target):
    if _target not in sys.path: sys.path.insert(0, _target)

def _exc_lookup(name, default):
    try:
        mod_name, _, cls_name = str(name).rpartition(".")
        if mod_name:
            mod = __import__(mod_name, fromlist=[cls_name])
            return getattr(mod, cls_name, default)
        return getattr(sys.modules.get("builtins"), str(name), default)
    except Exception:
        return default

# Optional Django bootstrap to avoid masking real failures by default.
if os.getenv("TESTGEN_ENABLE_DJANGO_BOOTSTRAP","0") in ("1","true","yes"):
    try:
        import django
        from django.conf import settings as _dj_settings
        from django import apps as _dj_apps
        if not _dj_settings.configured:
            _cfg = dict(
                DEBUG=True, SECRET_KEY='pytest-secret',
                DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3','NAME': ':memory:'}},
                INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages'],
                MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware'],
                USE_TZ=True, TIME_ZONE='UTC',
            )
            try: _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
            except Exception: pass
            try: _dj_settings.configure(**_cfg)
            except Exception: pass
        if not _dj_apps.ready:
            try: django.setup()
            except Exception: pass
        try: import django.contrib.auth.base_user as _dj_probe  # noqa
        except Exception as _e:
            _pytest.skip(f"Django core import failed safely: {_e.__class__.__name__}: {_e}", allow_module_level=True)
    except Exception as _e:
        _pytest.skip(f"Django bootstrap not available: {_e.__class__.__name__}: {_e}", allow_module_level=True)

import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
for __qt_root in ['PyQt5','PyQt6','PySide2','PySide6']:
    try:
        import importlib.util as _iu
        if _iu.find_spec(__qt_root) is None:
            raise ImportError
    except Exception:
        pass
# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

try:
    import pytest
    import inspect
    import types
    import math
    import Calculator as calc_module
except ImportError as e:
    import pytest
    pytest.skip(f"Required modules missing: {e}", allow_module_level=True)


Calculator = getattr(calc_module, "Calculator", None)
CalculatorError = getattr(calc_module, "CalculatorError", TypeError)


def _numeric_attrs(instance):
    # helper to find a plausible numeric state attribute on Calculator instances
    candidate_names = ("current", "current_value", "value", "result", "total")
    found = {}
    for name in candidate_names:
        if hasattr(instance, name):
            val = getattr(instance, name)
            if isinstance(val, (int, float)):
                found[name] = val
    return found


def _call_binary_like(method, a, b):
    # call a method that expects two numeric args (self, a, b) or (a, b) if it's a function
    sig = inspect.signature(method)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    if len(params) == 2:
        # signature like (self, a, b) or (a, b) if function
        return method(a, b)
    raise TypeError("Not a binary-like callable")


def _call_unary_like_on_instance(instance, method_name, value):
    # call method that expects a single numeric arg and operates on instance state
    method = getattr(instance, method_name)
    sig = inspect.signature(method)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    if len(params) == 1:
        return method(value)
    raise TypeError("Not a unary-like instance method")


def _almost_equal(a, b):
    # robust numeric comparison for floats/ints
    if isinstance(a, float) or isinstance(b, float):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    return a == b


def _expect_numeric_state_change(instance, before_state, after_state, expected_delta):
    # Assert at least one numeric tracked attribute changed by expected_delta
    for name, before_val in before_state.items():
        after_val = getattr(instance, name)
        if _almost_equal(after_val - before_val, expected_delta):
            return True
    # If none matched, raise assertion to fail test
    raise AssertionError(f"No numeric attribute changed by expected delta {expected_delta!r}. Before: {before_state}, After extracted: {{n: getattr(instance, n) for n in before_state.keys()}}")


def test___init__initializes_history_and_methods():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    assert Calculator is not None, "Calculator class must exist in module"
    # Act
    calc = Calculator()
    # Assert
    # public behavior: should be an instance of Calculator
    assert isinstance(calc, Calculator)
    # should expose add and subtract as callables
    assert hasattr(calc, "add"), "Calculator should have an 'add' method"
    assert callable(getattr(calc, "add"))
    assert hasattr(calc, "subtract"), "Calculator should have a 'subtract' method"
    assert callable(getattr(calc, "subtract"))
    # optional: if a history attribute exists it should be a list and start empty
    if hasattr(calc, "history"):
        history = getattr(calc, "history")
        assert isinstance(history, list), "history attribute, if present, must be a list"
        assert len(history) == 0, "history should be empty on initialization"


@pytest.mark.parametrize("a,b", [
    (1, 2),
    (0, 0),
    (-5, 3),
    (2.5, 0.5),
])
def test_add_handles_binary_and_unary_signatures(a, b):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calc = Calculator()
    add_attr = getattr(calc, "add", None)
    assert add_attr is not None, "Calculator must provide add"
    # Determine signature type: binary-like (a,b) or unary-like (adds to internal state)
    sig = inspect.signature(add_attr)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    if len(params) == 2:
        # Act
        result = add_attr(a, b)
        # Assert
        assert isinstance(result, (int, float)), "add(binary) should return numeric result"
        assert _almost_equal(result, a + b)
    elif len(params) == 1:
        # Act
        # Try to capture initial numeric state if available
        before = _numeric_attrs(calc)
        # If no numeric state attribute, assume base 0
        if not before:
            # attempt to set a common attribute if present
            for name in ("current", "current_value", "value", "result", "total"):
                if hasattr(calc, name):
                    before[name] = getattr(calc, name)
        base = next(iter(before.values())) if before else 0
        ret = add_attr(a)  # perform operation
        # Assert
        expected = base + a
        # If method returned a value, check it. Otherwise check state change.
        if ret is not None:
            assert isinstance(ret, (int, float)), "add(unary) when returning should be numeric"
            assert _almost_equal(ret, expected)
        else:
            # check that some numeric attribute changed by the expected delta
            after = _numeric_attrs(calc)
            if not after:
                pytest.skip("Calculator.add behaved unary but no numeric state attribute to verify")
            _expect_numeric_state_change(calc, before if before else {"_": base}, expected - (base if before else 0))
    else:
        pytest.skip("add has an unexpected signature; skipping test")


@pytest.mark.parametrize("bad_value", ["x", None, object()])
def test_add_raises_on_non_numeric(bad_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calc = Calculator()
    add_attr = getattr(calc, "add", None)
    assert add_attr is not None, "Calculator must provide add"
    # Determine expected exception type
    expected_exc = CalculatorError if CalculatorError is not None else TypeError
    sig = inspect.signature(add_attr)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    # Act / Assert
    if len(params) == 2:
        with pytest.raises(expected_exc):
            add_attr(1, bad_value)
    elif len(params) == 1:
        with pytest.raises(expected_exc):
            add_attr(bad_value)
    else:
        pytest.skip("add has an unexpected signature; skipping test")


@pytest.mark.parametrize("a,b", [
    (5, 2),
    (0, 0),
    (-3, -7),
    (3.5, 1.25),
])
def test_subtract_handles_binary_and_unary_signatures(a, b):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calc = Calculator()
    sub_attr = getattr(calc, "subtract", None)
    assert sub_attr is not None, "Calculator must provide subtract"
    sig = inspect.signature(sub_attr)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    if len(params) == 2:
        # Act
        result = sub_attr(a, b)
        # Assert
        assert isinstance(result, (int, float))
        assert _almost_equal(result, a - b)
    elif len(params) == 1:
        # Act
        before = _numeric_attrs(calc)
        if not before:
            base = 0
        else:
            base = next(iter(before.values()))
        ret = sub_attr(b)  # interpret as subtracting b from internal state
        expected = base - b
        if ret is not None:
            assert isinstance(ret, (int, float))
            assert _almost_equal(ret, expected)
        else:
            after = _numeric_attrs(calc)
            if not after:
                pytest.skip("Calculator.subtract behaved unary but no numeric state attribute to verify")
            _expect_numeric_state_change(calc, before if before else {"_": base}, -b)
    else:
        pytest.skip("subtract has an unexpected signature; skipping test")


@pytest.mark.parametrize("bad_value", ["y", None, object()])
def test_subtract_raises_on_non_numeric(bad_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calc = Calculator()
    sub_attr = getattr(calc, "subtract", None)
    assert sub_attr is not None, "Calculator must provide subtract"
    expected_exc = CalculatorError if CalculatorError is not None else TypeError
    sig = inspect.signature(sub_attr)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    # Act / Assert
    if len(params) == 2:
        with pytest.raises(expected_exc):
            sub_attr(1, bad_value)
    elif len(params) == 1:
        with pytest.raises(expected_exc):
            sub_attr(bad_value)
    else:
        pytest.skip("subtract has an unexpected signature; skipping test")
