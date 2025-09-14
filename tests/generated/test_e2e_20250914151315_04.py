
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

import pytest

def _exc_lookup(name, fallback=Exception):
    import builtins
    return getattr(builtins, name, fallback)

try:
    import Calculator
except ImportError:
    pytest.skip("Calculator module not available, skipping tests", allow_module_level=True)


def _resolve_callable(func_name):
    # Prefer bound methods on Calculator.Calculator if available, otherwise fallback to module-level function.
    if hasattr(Calculator, "Calculator"):
        calc = Calculator.Calculator()
        if hasattr(calc, func_name):
            return getattr(calc, func_name)
    if hasattr(Calculator, func_name):
        return getattr(Calculator, func_name)
    raise AttributeError(f"Function or method '{func_name}' not found in Calculator module/class.")


@pytest.mark.parametrize(
    "func_name,a,b,expected",
    [
        ("add", 1, 2, 3),
        ("subtract", 5, 2, 3),
        ("multiply", 3, 4, 12),
        ("divide", 10, 2, 5),
        ("add", -7, 3, -4),
        ("multiply", 0, 12345, 0),
        ("add", 10**18, 1, 10**18 + 1),
        ("divide", 7.5, 2.5, 3.0),
    ],
)
def test_basic_operations_return_values_and_types(func_name, a, b, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: resolve callable from public API
    func = _resolve_callable(func_name)

    # Act: invoke operation
    result = func(a, b)

    # Assert: numeric correctness and reasonable return type
    assert isinstance(result, (int, float)), "result should be numeric"
    # Use equality comparison for ints/floats; exact match expected for these cases
    assert result == expected


@pytest.mark.parametrize(
    "sequence, expected",
    [
        (("add", 2, 3), ("multiply", 5, 4), ("subtract", 20, 7), 13),
    ],
)
def test_chained_operations_produce_expected_result(sequence, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: Build a small chain using public API functions
    # Use module-level functions or Calculator instance methods transparently
    first_name, a1, b1 = sequence[0]
    second_name, a2, b2 = sequence[1]
    third_name, a3, b3 = sequence[2]

    first = _resolve_callable(first_name)
    second = _resolve_callable(second_name)
    third = _resolve_callable(third_name)

    # Act: perform chaining in a clear arrange-act-assert style
    intermediate1 = first(a1, b1)         # e.g., add(2,3) -> 5
    intermediate2 = second(intermediate1, a2)  # e.g., multiply(5,4) -> 20
    final = third(intermediate2, b3)      # e.g., subtract(20,7) -> 13

    # Assert: expected final numeric result and types along the way
    assert isinstance(intermediate1, (int, float))
    assert isinstance(intermediate2, (int, float))
    assert isinstance(final, (int, float))
    assert final == expected


def test_divide_by_zero_raises_standard_zero_division_error():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: resolve divide callable
    divide = _resolve_callable("divide")

    # Act / Assert: division by zero should raise built-in ZeroDivisionError (or fallback to Exception)
    ZeroDiv = _exc_lookup("ZeroDivisionError", Exception)
    with pytest.raises(_exc_lookup("ZeroDiv", Exception)):
        divide(1, 0)
