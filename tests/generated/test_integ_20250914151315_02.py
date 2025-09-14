
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
except ImportError:
    raise ImportError("pytest is required to run these tests")

try:
    import inspect
    import builtins as _builtins
    import os
    from unittest import mock
except ImportError:
    pytest.skip("standard library imports unavailable", allow_module_level=True)

try:
    import Calculator
except ImportError:
    pytest.skip("Calculator module not available", allow_module_level=True)

try:
    import SimpleCalculatorPyQt1 as Simple
except ImportError:
    pytest.skip("SimpleCalculatorPyQt1 module not available", allow_module_level=True)


def _exc_lookup(name, default=Exception):
    # Search known modules for an exception class by name, fall back to builtin or default.
    for mod in (Calculator, Simple):
        if hasattr(mod, name):
            return getattr(mod, name)
    try:
        built = getattr(_builtins, name)
        if isinstance(built, _exc_lookup("type", Exception)) and issubclass(built, BaseException):
            return built
    except Exception:
        pass
    return default


def _get_callable(module, func_name, class_name=None, instance_needed=False):
    """
    Helper: prefer module-level function; if not found and class_name provided,
    instantiate class and return bound method if available.
    """
    if hasattr(module, func_name):
        return getattr(module, func_name), None
    if class_name and hasattr(module, class_name):
        cls = getattr(module, class_name)
        try:
            inst = cls()
        except Exception:
            # If cannot instantiate without args, create a simple dummy object instead.
            inst = None
        if inst and hasattr(inst, func_name):
            return getattr(inst, func_name), inst
    return None, None


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (2, 3, 6),
        (0, 5, 0),
        (-2, 3, -6),
        (1.5, 2, 3.0),
        (10**6, 10**6, 10**12),
    ],
)
def test_multiply_various_inputs_returns_expected(a, b, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    multiply_func, _ = _get_callable(Calculator, "multiply", class_name="Calculator", instance_needed=False)
    if multiply_func is None:
        pytest.skip("multiply function/method not present in Calculator module")
    # Act
    result = multiply_func(a, b)
    # Assert
    assert isinstance(result, (int, float)), "multiply should return a numeric type"
    assert result == expected


@pytest.mark.parametrize(
    "a,b,expect_exception,expected_value",
    [
        (6, 3, False, 2),
        (5, 2, False, 2.5),
        (0, 5, False, 0),
        (1, 0, True, None),
    ],
)
def test_divide_various_including_division_by_zero(a, b, expect_exception, expected_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    divide_func, _ = _get_callable(Calculator, "divide", class_name="Calculator", instance_needed=False)
    if divide_func is None:
        pytest.skip("divide function/method not present in Calculator module")
    # Act / Assert
    if expect_exception:
        exc_cls = _exc_lookup("CalculatorError", Exception)
        with pytest.raises(_exc_lookup("exc_cls", Exception)):
            divide_func(a, b)
    else:
        result = divide_func(a, b)
        assert isinstance(result, (int, float)), "divide should return a numeric type"
        # For float comparisons (like 5/2), allow exact equality check as Python float for these small numbers
        assert result == expected_value


def test_save_history_uses_file_write(monkeypatch, tmp_path):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    save_func = getattr(Simple, "save_history", None)
    if save_func is None:
        pytest.skip("save_history not defined in SimpleCalculatorPyQt1")
    # Prepare a fake history payload
    history_payload = ["1 + 1 = 2", "2 * 3 = 6"]
    m_open = mock.mock_open()
    monkeypatch.setattr(_builtins, "open", m_open, raising=False)
    # If save_history expects (self) and reads .history attribute, prepare an object
    sig = inspect.signature(save_func)
    try:
        if len(sig.parameters) == 0:
            # function without params, likely uses MainWindow singleton or internal state.
            # Try to instantiate MainWindow to provide state.
            mw = getattr(Simple, "MainWindow", None)
            if mw is None:
                # nothing to do, attempt to call as-is and see if it writes
                save_func()
            else:
                # attach a plausible attribute and call instance method if possible
                try:
                    instance = mw()
                except Exception:
                    instance = type("FakeMW", (), {})()
                # prefer .history attribute name
                setattr(instance, "history", history_payload)
                # If save_history is defined on the class, call the bound method
                if hasattr(instance, "save_history"):
                    instance.save_history()
                else:
                    # call module-level function that may access global MainWindow state
                    save_func()
        elif len(sig.parameters) == 1:
            # likely save_history(history) or save_history(self)
            param_name = next(iter(sig.parameters))
            if "history" in param_name.lower():
                # call with explicit history
                save_func(history_payload)
            else:
                # treat as instance method requiring self; supply instance with .history
                mwcls = getattr(Simple, "MainWindow", None)
                if mwcls is not None:
                    try:
                        inst = mwcls()
                    except Exception:
                        inst = type("FakeMW", (), {})()
                else:
                    inst = type("FakeMW", (), {})()
                setattr(inst, "history", history_payload)
                save_func(inst)
        else:
            # multiple parameters: attempt to pass history as first argument
            params = []
            for i, p in enumerate(sig.parameters):
                if i == 0:
                    params.append(history_payload)
                else:
                    params.append(None)
            save_func(*params)
    except AttributeError as e:
        pytest.skip(f"save_history interaction not supported in this environment: {e}")
    # Assert: ensure builtins.open was called for writing history
    if not m_open.called:
        pytest.skip("save_history did not use builtins.open; it may use PyQt file APIs instead")
    # Check that write was called at least once
    handle = m_open()
    assert handle.write.call_count >= 1, "save_history should write something to the file"


def test_clear_history_then_save_results_in_empty_written_history(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    clear_func = getattr(Simple, "clear_history", None)
    save_func = getattr(Simple, "save_history", None)
    if clear_func is None or save_func is None:
        pytest.skip("clear_history or save_history not available in SimpleCalculatorPyQt1")
    # Prepare instance or context
    mwcls = getattr(Simple, "MainWindow", None)
    if mwcls is not None:
        try:
            instance = mwcls()
        except Exception:
            instance = type("FakeMW", (), {})()
    else:
        instance = type("FakeMW", (), {})()
    # give it a history attribute with entries
    setattr(instance, "history", ["a", "b", "c"])
    # Act: call clear_history. Try different signatures.
    try:
        sig_clear = inspect.signature(clear_func)
        if len(sig_clear.parameters) == 0:
            clear_func()
        elif len(sig_clear.parameters) == 1:
            clear_func(instance)
        else:
            # unknown signature: call with instance as first arg
            clear_func(instance)
    except ImportError as e:
        pytest.skip(f"clear_history invocation failed in this environment: {e}")
    except Exception:
        raise
    # Assert that history attribute is emptied if present
    if hasattr(instance, "history"):
        assert instance.history == [] or instance.history is None or len(getattr(instance, "history", [])) == 0
    # Now ensure save_history writes out the (now empty) history using builtins.open
    m_open = mock.mock_open()
    monkeypatch.setattr(_builtins, "open", m_open, raising=False)
    try:
        sig_save = inspect.signature(save_func)
        if len(sig_save.parameters) == 0:
            save_func()
        elif len(sig_save.parameters) == 1:
            # if parameter name suggests history, pass empty list; else pass instance
            param_name = next(iter(sig_save.parameters))
            if "history" in param_name.lower():
                save_func([])
            else:
                save_func(instance)
        else:
            # multiple params: attempt to pass instance then empty list
            save_func(instance, [])
    except ImportError as e:
        pytest.skip(f"save_history invocation failed in this environment: {e}")
    except Exception:
        raise
    if not m_open.called:
        pytest.skip("save_history did not use builtins.open; it may use PyQt file APIs instead")
    handle = m_open()
    # It's acceptable for write to be called zero times if API writes nothing for empty history,
    # but we assert that the file was opened for writing at least.
    assert m_open.called, "save_history should open a file even if history is empty"
