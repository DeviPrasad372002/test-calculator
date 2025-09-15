
# --- ENHANCED UNIVERSAL BOOTSTRAP ---
import os, sys, importlib.util as _iu, types as _types, pytest as _pytest, builtins as _builtins, warnings
STRICT = os.getenv("TESTGEN_STRICT", "1").lower() in ("1","true","yes")
STRICT_FAIL = os.getenv("TESTGEN_STRICT_FAIL","0").lower() in ("1","true","yes")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

_target = os.environ.get("TARGET_ROOT") or os.environ.get("ANALYZE_ROOT") or "target"
if _target and os.path.isdir(_target):
    _parent = os.path.abspath(os.path.join(_target, os.pardir))
    for p in (_parent, _target):
        if p not in sys.path:
            sys.path.insert(0, p)
    if "target" not in sys.modules:
        _pkg = _types.ModuleType("target")
        _pkg.__path__ = [_target]  # behave like a namespace package
        sys.modules["target"] = _pkg

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
    import builtins
    import os
    from unittest import mock
except Exception:  # pragma: no cover - defensive import skip
    import sys as _sys  # type: ignore
    raise

# Try to import the target modules; if they are not importable, skip the whole module.
try:
    import target.Calculator as calc_mod
except Exception:  # pragma: no cover
    pytest.skip("target.Calculator not available for tests", allow_module_level=True)

# SimpleCalculatorPyQt1 may depend on PyQt5; import if available, otherwise the UI tests will be skipped later.
try:
    import target.SimpleCalculatorPyQt1 as ui_mod  # type: ignore
except Exception:
    ui_mod = None  # UI-related tests will be skipped if module is not present


def _get_callable(module, name):
    """
    Retrieve a callable by name. Prefer a module-level callable; if absent,
    try to instantiate a Calculator class and obtain a bound method.
    If neither is available or callable cannot be constructed, skip the test.
    """
    # Module-level function
    if hasattr(module, name) and callable(getattr(module, name)):
        return getattr(module, name)

    # Try instance method on Calculator class
    if hasattr(module, "Calculator"):
        cls = getattr(module, "Calculator")
        try:
            inst = cls()
        except Exception:
            # Cannot instantiate Calculator without args; try to find an unbound function on the class
            if hasattr(cls, name) and callable(getattr(cls, name)):
                return getattr(cls, name)
            pytest.skip(f"Cannot instantiate {cls!r} to access {name!r}", allow_module_level=False)
        if hasattr(inst, name) and callable(getattr(inst, name)):
            return getattr(inst, name)

    pytest.skip(f"{name!r} callable not found in module {module!r}", allow_module_level=False)


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (3, 5, 15),
        (0, 12345, 0),
        (-4, 6, -24),
        (2.5, 4, 10.0),
        (-2.0, -3.5, 7.0),
    ],
)
def test_multiply_various_inputs_produces_expected_numeric_results(a, b, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    multiply = _get_callable(calc_mod, "multiply")

    # Act
    result = multiply(a, b)

    # Assert
    assert result == expected, f"multiply({a}, {b}) should be {expected}, got {result}"
    assert isinstance(result, type(expected)), "Result type should match expected type"


@pytest.mark.parametrize(
    "numerator,denominator,expected",
    [
        (6, 3, 2),
        (7, 2, 3.5),
        (0, 5, 0),
        (-10, 2, -5),
    ],
)
def test_divide_normal_cases_return_expected_values(numerator, denominator, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    divide = _get_callable(calc_mod, "divide")

    # Act
    result = divide(numerator, denominator)

    # Assert
    # numeric equality is sufficient; allow int/float equality. Also assert result is numeric type.
    assert result == expected, f"divide({numerator}, {denominator}) == {expected}, got {result}"
    assert isinstance(result, (int, float)), "Result should be numeric (int or float)"


def test_divide_by_zero_raises_calculator_error_or_zero_division_error():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    divide = _get_callable(calc_mod, "divide")
    # Prefer the custom CalculatorError if present; fall back to ZeroDivisionError
    expected_exc = getattr(calc_mod, "CalculatorError", ZeroDivisionError)

    # Act / Assert
    with pytest.raises(expected_exc):
        divide(1, 0)


@pytest.mark.skipif(ui_mod is None, reason="UI module not available; skipping save_history tests")
def test_save_history_writes_lines_and_handles_empty_history(tmp_path, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    if hasattr(ui_mod, "save_history") and callable(getattr(ui_mod, "save_history")):
        save_history = getattr(ui_mod, "save_history")
        # Prepare a non-empty history
        history = ["1 + 1 = 2", "2 * 3 = 6"]
        out_file = tmp_path / "history.txt"

        # Act
        save_history(history, str(out_file))

        # Assert
        assert out_file.exists(), "save_history should create the output file"
        content = out_file.read_text().splitlines()
        assert content == history, "File contents should match the provided history lines"

        # Now test empty history
        empty_file = tmp_path / "empty_history.txt"
        save_history([], str(empty_file))
        assert empty_file.exists(), "save_history should create a file even for empty history"
        assert empty_file.read_text() == "", "Empty history should produce an empty file"
    else:
        # If save_history is not a module-level callable, attempt to locate it on MainWindow
        if not hasattr(ui_mod, "MainWindow"):
            pytest.skip("Neither save_history nor MainWindow.save_history are available on UI module")
        MainWindow = getattr(ui_mod, "MainWindow")
        try:
            window = MainWindow()
        except Exception:
            pytest.skip("Cannot instantiate MainWindow to test save_history")
        if hasattr(window, "save_history") and callable(getattr(window, "save_history")):
            save_history = getattr(window, "save_history")
            history = ["a", "b"]
            out_file = tmp_path / "mw_history.txt"
            save_history(history, str(out_file))
            assert out_file.exists()
            assert out_file.read_text().splitlines() == history
        else:
            pytest.skip("save_history not available on MainWindow instance")


@pytest.mark.skipif(ui_mod is None, reason="UI module not available; skipping save_history error handling test")
def test_save_history_propagates_filesystem_errors(monkeypatch, tmp_path):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    if hasattr(ui_mod, "save_history") and callable(getattr(ui_mod, "save_history")):
        save_history = getattr(ui_mod, "save_history")
    else:
        if not hasattr(ui_mod, "MainWindow"):
            pytest.skip("Neither save_history nor MainWindow.save_history are available on UI module")
        MainWindow = getattr(ui_mod, "MainWindow")
        try:
            window = MainWindow()
        except Exception:
            pytest.skip("Cannot instantiate MainWindow to test save_history error handling")
        if hasattr(window, "save_history") and callable(getattr(window, "save_history")):
            save_history = getattr(window, "save_history")
        else:
            pytest.skip("save_history not available on MainWindow instance")

    path = tmp_path / "forbidden.txt"

    # Monkeypatch builtins.open to raise PermissionError to simulate filesystem permission issues.
    def fake_open(*args, **kwargs):
        raise PermissionError("Simulated permission denied")

    monkeypatch.setattr(builtins, "open", fake_open)

    # Act / Assert: expect a PermissionError or OSError to be raised when attempting to save.
    with pytest.raises((PermissionError, OSError)):
        save_history(["x"], str(path))
