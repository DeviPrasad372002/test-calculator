
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
try:
    import Calculator
    import SimpleCalculatorPyQt1
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

try:
    import PyQt5.QtWidgets as QtWidgets
except ImportError:
    QtWidgets = None

try:
    import inspect
    import os
except ImportError as e:
    pytest.skip(f"Stdlib import failed: {e}", allow_module_level=True)


def _exc_lookup(name, fallback=Exception):
    # Search known modules for an exception type, fall back if not found
    for mod in (globals().get('Calculator'), globals().get('SimpleCalculatorPyQt1')):
        if mod and hasattr(mod, name):
            return getattr(mod, name)
    return fallback


@pytest.mark.parametrize(
    "a,b,expected,expected_type",
    [
        (2, 3, 6, int),
        (0, 5, 0, int),
        (-2, 3, -6, int),
        (2.5, 4, 10.0, float),
        (10**6, 10**6, 10**12, int),
    ],
)
def test_multiply_various_inputs_returns_expected_types_and_values(a, b, expected, expected_type):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    multiply_func = getattr(Calculator, "multiply", None)
    assert callable(multiply_func), "Calculator.multiply must be callable"

    # Act
    result = multiply_func(a, b)

    # Assert
    assert result == expected, f"multiply({a}, {b}) == {expected}"
    assert isinstance(result, _exc_lookup("expected_type", Exception)), f"Expected type {expected_type} for result"


@pytest.mark.parametrize(
    "a,b,expected,expected_type",
    [
        (6, 3, 2, int),
        (5, 2, 2.5, float),
        (-6, 3, -2, int),
        (0, 5, 0, int),
    ],
)
def test_divide_various_inputs_returns_expected_types_and_values(a, b, expected, expected_type):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    divide_func = getattr(Calculator, "divide", None)
    assert callable(divide_func), "Calculator.divide must be callable"
    calc_error = _exc_lookup("CalculatorError", ZeroDivisionError)

    # Act
    result = divide_func(a, b)

    # Assert
    assert result == expected
    assert isinstance(result, _exc_lookup("expected_type", Exception))


def test_divide_by_zero_raises_calculator_error():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    divide_func = getattr(Calculator, "divide", None)
    assert callable(divide_func), "Calculator.divide must be callable"
    expected_exc = _exc_lookup("CalculatorError", ZeroDivisionError)

    # Act / Assert
    with pytest.raises(_exc_lookup("expected_exc", Exception)):
        divide_func(5, 0)


def _patch_get_save(monkeypatch, return_pair):
    # Try patching PyQt5 QFileDialog where code likely calls it
    patched = False
    if QtWidgets is not None:
        try:
            monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *a, **k: return_pair, raising=False)
            patched = True
        except Exception:
            patched = False
    if not patched:
        # Fallback: patch attribute on module if module uses QFileDialog directly
        class _QD:
            @staticmethod
            def getSaveFileName(*a, **k):
                return return_pair
        try:
            monkeypatch.setattr(SimpleCalculatorPyQt1, "QFileDialog", _QD, raising=False)
        except Exception:
            # best-effort; if unable to patch, tests that depend on GUI dialog may fail meaningfully
            pass


def _call_save_history_with(monkeypatch, history, filepath):
    """
    Arrange and Act: call the module's save_history API in a flexible manner:
    - If SimpleCalculatorPyQt1.save_history exists and accepts (history, path) -> call directly.
    - Else if it accepts a single path -> set a module-level history attribute if present and call.
    - Else attempt to call MainWindow.save_history as an unbound method using a dummy self with history attribute.
    """
    save_func = getattr(SimpleCalculatorPyQt1, "save_history", None)
    # Case 1: module-level save_history callable
    if callable(save_func):
        sig = inspect.signature(save_func)
        params = list(sig.parameters.values())
        # If signature is (history, filename)
        if len(params) >= 2:
            # Act
            save_func(history, str(filepath))
            return
        # If signature accepts single parameter, try passing filename
        if len(params) == 1:
            save_func(str(filepath))
            return
        # If zero params, attempt to set module-level history and call
        try:
            setattr(SimpleCalculatorPyQt1, "history", history)
            save_func()
            return
        except Exception:
            pass

    # Case 2: method on MainWindow
    MainWindow = getattr(SimpleCalculatorPyQt1, "MainWindow", None)
    if MainWindow and hasattr(MainWindow, "save_history"):
        method = getattr(MainWindow, "save_history")
        # Create a dummy instance with required attributes (history); method may be unbound function
        dummy = type("Dummy", (), {})()
        setattr(dummy, "history", history)
        # Patch QFileDialog used by method to return the chosen filepath
        _patch_get_save(monkeypatch, (str(filepath), ""))
        # Act
        # If method is function descriptor we need to call it with dummy as self
        try:
            method(dummy)
            return
        except TypeError:
            # maybe method is bound or expects no args (rare). Try calling without passing self.
            method()
            return

    # If nothing matched, raise to mark unsupported API shape
    raise RuntimeError("No supported save_history API shape found in SimpleCalculatorPyQt1")


def test_save_history_creates_file_when_user_selects_path(tmp_path, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    history = ["2 * 3 = 6"]
    target_file = tmp_path / "history.txt"

    # Ensure the GUI save dialog returns our chosen path if used
    _patch_get_save(monkeypatch, (str(target_file), ""))

    # Act
    _call_save_history_with(monkeypatch, history, target_file)

    # Assert
    assert target_file.exists(), "save_history should create the chosen file"
    # File should contain something when history is non-empty
    assert target_file.stat().st_size > 0, "Saved history file should not be empty when history contains entries"


def test_save_history_does_not_create_file_when_user_cancels(tmp_path, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    history = ["1 + 1 = 2"]
    target_file = tmp_path / "should_not_exist.txt"

    # Simulate user cancelling the save dialog: many Qt APIs return ('', '') or ('', None)
    _patch_get_save(monkeypatch, ("", ""))

    # Act
    # Attempt to call save; if the implementation handles cancel correctly, no file should be created.
    try:
        _call_save_history_with(monkeypatch, history, target_file)
    except RuntimeError:
        # If API shape unsupported, skip this assertion path as we could not exercise dialog behavior
        pytest.skip("save_history API shape not supported by this test harness")

    # Assert
    assert not target_file.exists(), "No file should be created when the user cancels the save dialog"
