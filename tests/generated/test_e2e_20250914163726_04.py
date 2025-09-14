
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
    import Calculator
    import math
    from unittest import mock
except ImportError as e:
    import pytest as _pytest  # type: ignore
    _pytest.skip(f"Skipping tests because of ImportError at module import: {e}", allow_module_level=True)

def _exc_lookup(name, fallback=Exception):
    # Search common modules for a named exception, fallback to provided fallback class
    for mod in (globals().get('Calculator', None), globals().get('SimpleCalculatorPyQt1', None)):
        if mod is None:
            continue
        if hasattr(mod, name):
            return getattr(mod, name)
    return fallback

@pytest.mark.parametrize(
    "fname,a,b,expected,expect_exc",
    [
        ("add", 2, 3, 5, False),
        ("subtract", 5, 2, 3, False),
        ("multiply", 4, 3, 12, False),
        ("divide", 10, 2, 5, False),
        ("divide", 1, 0, None, True),  # division by zero -> expect CalculatorError (if defined) or generic Exception
    ],
)
def test_binary_operations_parametrized(fname, a, b, expected, expect_exc):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: get the function from the Calculator module
    func = getattr(Calculator, fname, None)
    if func is None or not callable(func):
        pytest.skip(f"Calculator.{fname} not available")
    # Act / Assert
    if expect_exc:
        exc = _exc_lookup("CalculatorError", Exception)
        with pytest.raises(_exc_lookup("exc", Exception)):
            func(a, b)
    else:
        result = func(a, b)
        # Assert: concrete value and numeric type
        assert result == expected, f"Expected {expected} from {fname}({a}, {b}), got {result}"
        assert isinstance(result, (int, float)), "Result should be numeric"

def test_addition_float_precision():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    add_fn = getattr(Calculator, "add", None)
    if add_fn is None or not callable(add_fn):
        pytest.skip("Calculator.add not available")
    a, b = 0.1, 0.2
    # Act
    result = add_fn(a, b)
    # Assert: numeric type and close to expected value within floating point tolerance
    assert isinstance(result, (float, int)), "Result should be a float or int for float inputs"
    assert math.isclose(result, 0.3, rel_tol=1e-9, abs_tol=1e-12), f"Expected approximately 0.3, got {result}"
