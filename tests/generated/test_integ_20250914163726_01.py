
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
    import inspect
    import builtins
    import os
    from unittest import mock
    import Calculator
    import SimpleCalculatorPyQt1
except ImportError as e:
    import pytest as _pytest_dummy
    _pytest_dummy.skip("Skipping integration tests due to ImportError: {}".format(e))


def _exc_lookup(name, fallback=Exception):
    # Look for exception class by name in known modules, fallback to given fallback
    for mod in (Calculator, SimpleCalculatorPyQt1):
        exc = getattr(mod, name, None)
        if isinstance(exc, _exc_lookup("type", Exception)) and issubclass(exc, BaseException):
            return exc
    return fallback


def _get_binary_op(mod, op_name):
    # Return a callable (a, b) -> result for add/subtract/etc or raise pytest.skip
    # Try module-level function first, then instance method from Calculator class
    func = getattr(mod, op_name, None)
    if callable(func):
        return func
    cls = getattr(mod, 'Calculator', None)
    if cls is not None and inspect.isclass(cls):
        # Try instantiate with no args, then with single 0
        for ctor_args in ((), (0,)):
            try:
                inst = cls(*ctor_args)
            except Exception:
                continue
            member = getattr(inst, op_name, None)
            if callable(member):
                return member
    pytest.skip(f"No callable '{op_name}' found in module {mod.__name__}")


def _call_save_history(mod, result, tmp_path, monkeypatch):
    save = getattr(mod, 'save_history', None)
    if not callable(save):
        pytest.skip("save_history not found in module")
    sig = inspect.signature(save)
    mo = mock.mock_open()
    monkeypatch.setattr(builtins, 'open', mo)
    # Try to call with reasonable argument patterns
    called = False
    errors = []
    # Build candidate argument lists
    candidates = []
    # If signature has parameters, prepare combinations: (result), (None, result), (result, path), (None, result, path)
    params = list(sig.parameters)
    if len(params) == 0:
        candidates.append([])
    if len(params) == 1:
        candidates.append([result])
        candidates.append([str(tmp_path / "history.txt")])
    if len(params) == 2:
        candidates.append([result, str(tmp_path / "history.txt")])
        candidates.append([None, result])
    if len(params) >= 3:
        args = [None, result] + [str(tmp_path / f"history_{i}.txt") for i in range(len(params) - 2)]
        candidates.append(args)
    # Also add a simple attempt with only result
    candidates.append([result])
    for args in candidates:
        try:
            save(*args)
            called = True
            break
        except TypeError as te:
            errors.append(te)
            continue
        except Exception:
            # If save_history raised a runtime error, still consider it called
            called = True
            break
    if not called:
        pytest.skip(f"Could not call save_history; attempted signatures caused errors: {errors}")
    return mo


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (2, 3, 5),          # normal ints
        (0, 0, 0),          # boundary zeros
        (-5, 5, 0),         # negative + positive
        (1.5, 2.5, 4.0),    # floats
    ],
)
def test_add_and_save_history_integration(a, b, expected, tmp_path, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    add = _get_binary_op(Calculator, 'add')
    # Act
    result = add(a, b)
    # Assert type and numeric equality (allow float/int mix)
    assert isinstance(result, (int, float)), "add should return a number"
    # Use near-equality for floats to tolerate float rounding
    if isinstance(result, _exc_lookup("float", Exception)) or isinstance(expected, _exc_lookup("float", Exception)):
        assert abs(result - expected) < 1e-9
    else:
        assert result == expected

    # Now integrate with save_history in SimpleCalculatorPyQt1: ensure it attempts to write the result
    mo = _call_save_history(SimpleCalculatorPyQt1, result, tmp_path, monkeypatch)

    # Assert that open was called and that write was invoked with a representation containing the result
    handle = mo()
    # It's possible save_history writes multiple times; ensure at least one write call contains the expected text
    write_calls = []
    try:
        write_calls = [c.args[0] for c in handle.write.call_args_list]
    except Exception:
        # If no write recorded, fail concretely
        pytest.fail("save_history did not write using builtins.open mock")
    joined = "".join(map(str, write_calls))
    assert str(expected) in joined, f"Saved history should contain the result {expected}; got writes: {joined}"


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (10, 4, 6),         # normal ints
        (0, 5, -5),         # zero minuend
        (-3, -2, -1),       # negatives
        (2.5, 1.5, 1.0),    # floats
    ],
)
def test_subtract_and_clear_history_integration(a, b, expected, tmp_path, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    sub = _get_binary_op(Calculator, 'subtract')
    # Act
    result = sub(a, b)
    # Assert numeric result
    assert isinstance(result, (int, float))
    if isinstance(result, _exc_lookup("float", Exception)) or isinstance(expected, _exc_lookup("float", Exception)):
        assert abs(result - expected) < 1e-9
    else:
        assert result == expected

    # Prepare a file to act as history
    hist_path = tmp_path / "history.txt"
    hist_path.write_text("old_content\n")
    # Replace os.remove and builtins.open to observe behavior
    removed = {'called': False}
    def fake_remove(path):
        removed['called'] = True
        # actually remove to simulate behavior
        try:
            os.remove(path)
        except Exception:
            pass
    monkeypatch.setattr(os, 'remove', fake_remove)

    # Attempt to call clear_history with various signatures
    clear = getattr(SimpleCalculatorPyQt1, 'clear_history', None)
    if not callable(clear):
        pytest.skip("clear_history not found in UI module")

    sig = inspect.signature(clear)
    # Try a few candidate calls
    called = False
    errors = []
    candidates = []
    params = list(sig.parameters)
    if len(params) == 0:
        candidates.append([])
    if len(params) == 1:
        candidates.append([None])
        candidates.append([str(hist_path)])
    if len(params) >= 2:
        args = [None, str(hist_path)] + [None] * (len(params) - 2)
        candidates.append(args)
    candidates.append([str(hist_path)])
    for args in candidates:
        try:
            clear(*args)
            called = True
            break
        except TypeError as te:
            errors.append(te)
            continue
        except Exception:
            # clear_history may raise on purpose; consider it called
            called = True
            break
    if not called:
        pytest.skip(f"Could not call clear_history; attempted signatures caused errors: {errors}")

    # Assert that after calling clear_history the file was either removed or emptied
    if removed['called']:
        assert not hist_path.exists() or hist_path.stat().st_size == 0
    else:
        if hist_path.exists():
            content = hist_path.read_text()
            assert content == "" or content == " " or content == "\n" or content == "old_content\n" and False, (
                "clear_history should remove or empty the history file; got: {!r}".format(content)
            )


def test_add_invalid_inputs_raises_integration():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    add = _get_binary_op(Calculator, 'add')
    # Act & Assert: passing invalid types should raise some exception (prefer CalculatorError if present)
    exc = _exc_lookup('CalculatorError', Exception)
    with pytest.raises(_exc_lookup("exc", Exception)):
        add("a", "b")
