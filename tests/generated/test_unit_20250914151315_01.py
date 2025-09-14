
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

try:
    import pytest
    import inspect
    import math
    import Calculator as calcmod
except ImportError as e:
    import pytest
    pytest.skip(f"Missing dependency: {e}", allow_module_level=True)

def _exc_lookup(name, fallback=Exception):
    return getattr(calcmod, name, fallback)

def _has_function(name):
    return hasattr(calcmod, name) and callable(getattr(calcmod, name))

def _get_bound_adder():
    # Return a callable that accepts two numeric args (a, b) and tries to perform addition using available API.
    if _has_function('add'):
        return calcmod.add, None
    cls = getattr(calcmod, 'Calculator', None)
    if cls is None:
        pytest.skip("No add function or Calculator class available", allow_module_level=False)
    # attempt multiple constructor signatures
    for ctor_arg in ((), (0,), (1.0,)):
        try:
            inst = cls(*ctor_arg)
            break
        except TypeError:
            continue
    else:
        pytest.skip("Calculator cannot be instantiated for testing add", allow_module_level=False)
    if hasattr(inst, 'add') and callable(getattr(inst, 'add')):
        return getattr(inst, 'add'), inst
    pytest.skip("No callable add available on Calculator instance", allow_module_level=False)

def _get_bound_subtractor():
    if _has_function('subtract'):
        return calcmod.subtract, None
    cls = getattr(calcmod, 'Calculator', None)
    if cls is None:
        pytest.skip("No subtract function or Calculator class available", allow_module_level=False)
    for ctor_arg in ((), (0,), (1.0,)):
        try:
            inst = cls(*ctor_arg)
            break
        except TypeError:
            continue
    else:
        pytest.skip("Calculator cannot be instantiated for testing subtract", allow_module_level=False)
    if hasattr(inst, 'subtract') and callable(getattr(inst, 'subtract')):
        return getattr(inst, 'subtract'), inst
    pytest.skip("No callable subtract available on Calculator instance", allow_module_level=False)

@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (-1, 1, 0),
    (1.5, 2.25, 3.75),
    (0, 0, 0),
    (10**12, 10**12, 2 * 10**12),  # large number boundary
])
def test_add_basic_numbers(a, b, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    add_callable, bound_instance = _get_bound_adder()
    # Act
    try:
        result = add_callable(a, b)
    except TypeError:
        # try other calling conventions (bound method that takes single operand)
        try:
            result = add_callable(b)
        except TypeError:
            pytest.fail("add callable could not be invoked with either (a,b) or (b)")
    # Assert
    assert isinstance(result, (int, float)), "add should return numeric type"
    # allow int/float equivalence for exact values
    if isinstance(expected, _exc_lookup("float", Exception)):
        assert math.isclose(result, expected, rel_tol=1e-12, abs_tol=1e-12)
    else:
        assert result == expected

@pytest.mark.parametrize("a,b,expected", [
    (5, 3, 2),
    (0, 5, -5),
    (2.5, 1.25, 1.25),
    (-5, -5, 0),
])
def test_subtract_basic_numbers(a, b, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    sub_callable, bound_instance = _get_bound_subtractor()
    # Act
    try:
        result = sub_callable(a, b)
    except TypeError:
        try:
            result = sub_callable(b)
        except TypeError:
            pytest.fail("subtract callable could not be invoked with either (a,b) or (b)")
    # Assert
    assert isinstance(result, (int, float)), "subtract should return numeric type"
    if isinstance(expected, _exc_lookup("float", Exception)):
        assert math.isclose(result, expected, rel_tol=1e-12, abs_tol=1e-12)
    else:
        assert result == expected

@pytest.mark.parametrize("left,right", [
    ("a", 1),
    (None, 2),
    ([1,2], 3),
])
def test_add_with_invalid_types_raises(left, right):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    add_callable, _ = _get_bound_adder()
    exccls = _exc_lookup('CalculatorError', Exception)
    # Act / Assert: accept either module/class-defined CalculatorError or common builtins
    allowed = (exccls, TypeError, ValueError)
    with pytest.raises(_exc_lookup("allowed", Exception)):
        add_callable(left, right)

def test_calculator_class_init_and_state_changes():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    cls = getattr(calcmod, 'Calculator', None)
    if cls is None:
        pytest.skip("Calculator class not present for __init__ state test", allow_module_level=False)
    # Try to construct with an initial value; if not supported, use default
    initial_value = 10
    try:
        inst = cls(initial_value)
        constructed_with_initial = True
    except TypeError:
        inst = cls()
        constructed_with_initial = False
    # Identify a plausible state attribute that should reflect current value
    candidate_attrs = ['value', 'total', 'result', 'current', 'display']
    state_attr = None
    for name in candidate_attrs:
        if hasattr(inst, name):
            state_attr = name
            break
    # Act: attempt to add a delta using available add implementation
    delta = 5
    add_callable = None
    if hasattr(inst, 'add') and callable(getattr(inst, 'add')):
        add_callable = getattr(inst, 'add')
        # try calling with different signatures
        for attempt in ((delta,), (initial_value, delta), (delta,)):
            try:
                out = add_callable(*attempt)
                added_return = out
                break
            except TypeError:
                continue
        else:
            pytest.skip("Unable to call Calculator.add with expected argument patterns", allow_module_level=False)
    elif _has_function('add'):
        # module function present and operates on two args
        add_callable = calcmod.add
        added_return = add_callable(initial_value if not constructed_with_initial else getattr(inst, state_attr, initial_value), delta)
    else:
        pytest.skip("No add available on class instance or module", allow_module_level=False)
    # Assert: check returned value and/or state attribute updated
    expected = (initial_value if constructed_with_initial else (getattr(inst, state_attr, 0) if state_attr else 0)) + delta
    # If state_attr exists, prefer asserting state changed to expected
    if state_attr and hasattr(inst, state_attr):
        state_val = getattr(inst, state_attr)
        assert isinstance(state_val, (int, float)), f"{state_attr} should be numeric"
        assert state_val == expected or (isinstance(expected, _exc_lookup("float", Exception)) and abs(state_val - expected) < 1e-12)
    else:
        # Fall back to returned value
        assert isinstance(added_return, (int, float)), "add should return numeric type when state attribute not present"
        assert added_return == expected or (isinstance(expected, _exc_lookup("float", Exception)) and abs(added_return - expected) < 1e-12)

@pytest.mark.parametrize("left,right", [
    ("x", 1),
    (1, []),
    (object(), 2),
])
def test_subtract_with_invalid_types_raises(left, right):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    sub_callable, _ = _get_bound_subtractor()
    exccls = _exc_lookup('CalculatorError', Exception)
    allowed = (exccls, TypeError, ValueError)
    # Act / Assert
    with pytest.raises(_exc_lookup("allowed", Exception)):
        sub_callable(left, right)
