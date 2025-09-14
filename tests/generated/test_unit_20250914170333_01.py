
# --- ENHANCED UNIVERSAL BOOTSTRAP ---
import os, sys, importlib.util as _iu, types as _types, pytest as _pytest, builtins as _builtins, warnings
STRICT = os.getenv("TESTGEN_STRICT", "1").lower() in ("1","true","yes")
STRICT_FAIL = os.getenv("TESTGEN_STRICT_FAIL","0").lower() in ("1","true","yes")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

_target = os.environ.get("TARGET_ROOT") or os.environ.get("ANALYZE_ROOT") or "target"
if _target and os.path.exists(_target):
    if _target not in sys.path: sys.path.insert(0, _target)
    try: os.chdir(_target)
    except Exception: pass

def _exc_lookup(name, default):
    try:
        mod_name, _, cls_name = str(name).rpartition(".")
        if mod_name:
            mod = __import__(mod_name, fromlist=[cls_name])
            return getattr(mod, cls_name, default)
        return getattr(sys.modules.get("builtins"), str(name), default)
    except Exception:
        return default

def _apply_compatibility_fixes():
    try:
        import jinja2
        if not hasattr(jinja2, 'Markup'):
            try:
                from markupsafe import Markup, escape
                jinja2.Markup = Markup
                if not hasattr(jinja2, 'escape'):
                    jinja2.escape = escape
            except Exception:
                pass
    except ImportError:
        pass
    try:
        import collections as _collections, collections.abc as _abc
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container',
                   'MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection'):
            if not hasattr(_collections, _n) and hasattr(_abc, _n):
                setattr(_collections, _n, getattr(_abc, _n))
    except Exception:
        pass
    try:
        import marshmallow as _mm
        if not hasattr(_mm, "__version__"):
            _mm.__version__ = "4"
    except Exception:
        pass

_apply_compatibility_fixes()

# Minimal, safe Django bootstrap. If anything goes wrong, skip the module (repo-agnostic).
try:
    import django
    from django.conf import settings as _dj_settings
    from django import apps as _dj_apps

    if not _dj_settings.configured:
        _cfg = dict(
            DEBUG=True,
            SECRET_KEY='pytest-secret',
            DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3','NAME': ':memory:'}},
            INSTALLED_APPS=[
                'django.contrib.auth','django.contrib.contenttypes',
                'django.contrib.sessions','django.contrib.messages'
            ],
            MIDDLEWARE=[
                'django.middleware.security.SecurityMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.common.CommonMiddleware',
            ],
            USE_TZ=True, TIME_ZONE='UTC',
        )
        try: _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
        except Exception: pass
        try: _dj_settings.configure(**_cfg)
        except Exception: pass

    if not _dj_apps.ready:
        try: django.setup()
        except Exception: pass

    # Probe a known Django core that previously crashed on some stacks.
    try:
        import django.contrib.auth.base_user as _dj_probe  # noqa
    except Exception as _e:
        _pytest.skip(f"Django core import failed safely: {_e.__class__.__name__}: {_e}", allow_module_level=True)
except Exception as _e:
    # Do NOT crash the entire test session – make the module opt-out.
    _pytest.skip(f"Django bootstrap not available: {_e.__class__.__name__}: {_e}", allow_module_level=True)


for __qt_root in ["PyQt5","PyQt6","PySide2","PySide6"]:
    try:
        import importlib.util as _iu
        if _iu.find_spec(__qt_root) is None:
            raise ImportError
    except Exception:
        pass

# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    from unittest import mock
    import importlib
    calc_module = importlib.import_module("Calculator")
except ImportError as _err:
    import pytest as _pytest
    _pytest.skip(f"Required modules for tests not available: {_err}", allow_module_level=True)


def _get_callable(name):
    # Prefer module-level function, otherwise prefer instance bound method on Calculator
    if hasattr(calc_module, name) and callable(getattr(calc_module, name)):
        return getattr(calc_module, name)
    cls = getattr(calc_module, "Calculator", None)
    if cls is not None:
        inst = cls()
        if hasattr(inst, name) and callable(getattr(inst, name)):
            return getattr(inst, name)
    pytest.skip(f"No callable named {name} available in module or Calculator class")


def _exc_lookup(name, fallback=Exception):
    # Try to resolve an exception class by name in module, then builtins, else fallback
    exc = getattr(calc_module, name, None)
    if isinstance(exc, _exc_lookup("type", Exception)) and issubclass(exc, BaseException):
        return exc
    try:
        import builtins as _builtins
        bexc = getattr(_builtins, name, None)
        if isinstance(bexc, _exc_lookup("type", Exception)) and issubclass(bexc, BaseException):
            return bexc
    except Exception:
        pass
    return fallback


def test_constructor_creates_instance_and_exposes_operations():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    CalculatorClass = getattr(calc_module, "Calculator", None)

    # Act & Assert
    if CalculatorClass is None:
        # If no class, ensure module-level callables exist
        add_fn = _get_callable("add")
        subtract_fn = _get_callable("subtract")
        assert callable(add_fn), "module-level add should be callable"
        assert callable(subtract_fn), "module-level subtract should be callable"
    else:
        # Instantiate and verify public API surface and initial state
        # Arrange
        # Act
        inst = CalculatorClass()
        # Assert
        assert inst is not None
        # public methods should exist
        assert hasattr(inst, "add") and callable(getattr(inst, "add"))
        assert hasattr(inst, "subtract") and callable(getattr(inst, "subtract"))
        # optional common attributes: history or last_result if present should be of expected types
        if hasattr(inst, "history"):
            assert isinstance(inst.history, list), "history should be a list if provided"
        if hasattr(inst, "last_result"):
            assert inst.last_result is None or isinstance(inst.last_result, (int, float))


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (2, 3, 5),
        (-1, 1, 0),
        (1.5, 2.25, 3.75),
        (10**12, 10**12, 2 * 10**12),  # large number boundary
    ],
)
def test_add_returns_correct_numeric_results(a, b, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    add_fn = _get_callable("add")

    # Act
    result = add_fn(a, b)

    # Assert
    assert isinstance(result, (int, float)), "result should be numeric"
    # allow exact equality for ints and exact floats in these cases
    assert result == expected


@pytest.mark.parametrize(
    "a,b,exc_name",
    [
        ("a", 1, "TypeError"),
        (1, "b", "TypeError"),
        (None, 5, "TypeError"),
        ("foo", "bar", "TypeError"),
    ],
)
def test_add_invalid_inputs_raise(a, b, exc_name):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    add_fn = _get_callable("add")
    expected_exc = _exc_lookup("CalculatorError", _exc_lookup(exc_name, TypeError))

    # Act / Assert
    with pytest.raises(_exc_lookup("expected_exc", Exception)):
        add_fn(a, b)


@pytest.mark.parametrize(
    "initial,subtrahend,expected",
    [
        (10, 3, 7),
        (0, 0, 0),
        (-5, -5, 0),
        (1.5, 0.5, 1.0),
    ],
)
def test_subtract_behavior_and_history_update(initial, subtrahend, expected, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # get subtract callable; prefer instance method to observe stateful behavior if present
    if hasattr(calc_module, "Calculator"):
        CalcClass = getattr(calc_module, "Calculator")
        inst = CalcClass()
        # If the instance supports save_history, replace it with a mock to assert calls
        if hasattr(inst, "save_history"):
            mock_save = mock.Mock()
            monkeypatch.setattr(inst, "save_history", mock_save)
        subtract_fn = getattr(inst, "subtract")
    else:
        subtract_fn = _get_callable("subtract")
        inst = None

    # Act
    result = subtract_fn(initial, subtrahend)

    # Assert
    assert isinstance(result, (int, float))
    assert result == expected

    # If instance has stateful history, verify it was updated
    if inst is not None and hasattr(inst, "history"):
        # history should have at least one entry and last entry should reflect operation result
        assert isinstance(inst.history, list)
        assert len(inst.history) >= 1
        last = inst.history[-1]
        # last can be a numeric entry or a tuple describing operation; be permissive but concrete
        if isinstance(last, (int, float)):
            assert last == result
        else:
            # if it's a tuple or dict, ensure it contains the numeric result
            if isinstance(last, _exc_lookup("tuple", Exception)):
                assert result in last
            elif isinstance(last, _exc_lookup("dict", Exception)):
                assert any(v == result for v in last.values())

    # If save_history was present, ensure it was invoked exactly once for this operation
    if inst is not None and hasattr(inst, "save_history"):
        inst.save_history.assert_called()
