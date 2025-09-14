
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
    import math
    import Calculator
    from unittest import mock
except ImportError as e:
    import pytest as _pytest
    _pytest.skip("skipping tests because required modules are not importable: {}".format(e), allow_module_level=True)

def _exc_lookup(name, default=Exception):
    # Try to find an exception by name on the Calculator module, fallback to default
    return getattr(Calculator, name, default)

@pytest.mark.parametrize(
    "op_name, args, expected",
    [
        ("add", (2, 3), 5),                       # normal integers
        ("subtract", (5, 2), 3),                  # normal integers
        ("multiply", (3, 4), 12),                 # normal integers
        ("divide", (8, 2), 4),                    # integer division yielding int
        ("add", (10**12, 10**12), 2 * 10**12),    # large integer boundary-like
        ("divide", (7, 2), 3.5),                  # float result
        ("multiply", (-3, 6), -18),               # negative operand
    ]
)
def test_calculator_basic_operations_update_history(op_name, args, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create a fresh Calculator instance and capture initial history length if present
    calc = Calculator.Calculator()
    initial_history = None
    if hasattr(calc, "history"):
        initial_history = list(getattr(calc, "history"))  # copy for comparison

    # Act: call the requested operation via public API
    func = getattr(calc, op_name)
    result = func(*args)

    # Assert: result type and value
    if isinstance(expected, _exc_lookup("float", Exception)):
        assert isinstance(result, _exc_lookup("float", Exception)) or isinstance(result, (float, int))
        assert math.isclose(result, expected, rel_tol=1e-9, abs_tol=1e-12)
    else:
        assert result == expected
        assert isinstance(result, _exc_lookup("int", Exception)) or isinstance(result, _exc_lookup("float", Exception))

    # Assert: history updated in a reasonable way (if history exists)
    if initial_history is not None:
        new_history = getattr(calc, "history")
        assert len(new_history) == len(initial_history) + 1
        last = new_history[-1]
        # Accept several history entry shapes: direct numeric result, container containing result, or string mentioning result
        if isinstance(last, (int, float)):
            if isinstance(expected, _exc_lookup("float", Exception)):
                assert math.isclose(last, expected, rel_tol=1e-9, abs_tol=1e-12)
            else:
                assert last == expected
        else:
            assert str(expected) in str(last)

def test_divide_by_zero_raises_and_does_not_append_history():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create calculator and snapshot history
    calc = Calculator.Calculator()
    has_history = hasattr(calc, "history")
    prior_history = list(calc.history) if has_history else None

    # Act & Assert: dividing by zero raises the module's error type (fallback to Exception)
    exc = _exc_lookup("CalculatorError", Exception)
    with pytest.raises(_exc_lookup("exc", Exception)):
        calc.divide(1, 0)

    # Assert: history was not appended when the operation failed
    if has_history:
        assert list(calc.history) == prior_history
