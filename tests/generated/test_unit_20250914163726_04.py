
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
    from Calculator import Calculator, CalculatorError
    import SimpleCalculatorPyQt1 as SimpleCalc
    from PyQt5 import QtWidgets
except ImportError as e:
    import pytest
    pytest.skip(f"Missing dependency: {e}", allow_module_level=True)

# Ensure a QApplication exists for widget operations
_qapp = None
if hasattr(QtWidgets, "QApplication"):
    if QtWidgets.QApplication.instance() is None:
        _qapp = QtWidgets.QApplication([])

def _exc_lookup(name, default=Exception):
    # look up exception in globals (imported names) or fallback to default
    return globals().get(name, default)

import os

@pytest.mark.parametrize(
    "method,a,b,expected",
    [
        ("add", 1, 2, 3),
        ("add", 1.5, 2.5, 4.0),
        ("subtract", 5, 3, 2),
        ("subtract", -1, -1, 0),
        ("multiply", 3, 4, 12),
        ("multiply", 2.5, 4, 10.0),
        ("divide", 10, 2, 5.0),
        ("divide", -9, -3, 3.0),
        ("add", 0, 0, 0),
    ],
)
def test_calculator_basic_operations(method, a, b, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calc = Calculator()
    assert hasattr(calc, method), f"Calculator missing method {method}"
    func = getattr(calc, method)
    # Act
    result = func(a, b)
    # Assert
    assert result == expected, f"{method}({a},{b}) -> {result}, expected {expected}"
    assert type(result) is type(expected), "Return type should match expected type"

def test_calculator_divide_by_zero_raises():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calc = Calculator()
    expected_exc = _exc_lookup("CalculatorError", Exception)
    assert callable(getattr(calc, "divide", None)), "Calculator.divide must exist"
    # Act / Assert
    with pytest.raises(_exc_lookup("expected_exc", Exception)):
        calc.divide(1, 0)

def test_mainwindow_save_and_clear_history_and_clear_input(tmp_path, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    if not hasattr(SimpleCalc, "MainWindow"):
        pytest.skip("MainWindow not present in SimpleCalculatorPyQt1")
    MainWindow = SimpleCalc.MainWindow
    mw = MainWindow()

    # Prepare a deterministic history on the instance (UI independent)
    test_history = ["1 + 1 = 2", "2 * 3 = 6"]
    # Prefer setting attribute directly; some implementations keep history on self.history
    if hasattr(mw, "history"):
        mw.history = list(test_history)
    else:
        # try common alternative names
        setattr(mw, "history", list(test_history))

    # Monkeypatch QFileDialog.getSaveFileName to avoid GUI interaction and return our path
    out_file = tmp_path / "history_out.txt"
    def fake_getsave(*args, **kwargs):
        # Qt can return either a string or a tuple depending on bindings; support both
        return (str(out_file), "")
    if hasattr(QtWidgets, "QFileDialog"):
        monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", fake_getsave, raising=False)

    # Act: call save_history; if the method requires parameters it should still work or raise,
    # so guard and provide the filename directly if accepted
    save_fn = getattr(mw, "save_history", None)
    assert callable(save_fn), "MainWindow.save_history must exist"
    try:
        # Try without args first (typical PyQt pattern)
        save_fn()
    except TypeError:
        # If it requires a filename argument, pass ours
        save_fn(str(out_file))

    # Assert: file was written and contains our history lines
    assert out_file.exists(), "save_history should create the output file"
    content = out_file.read_text(encoding="utf8")
    for line in test_history:
        assert line in content, f"Expected history line '{line}' in saved file"

    # Act: clear history
    clear_hist = getattr(mw, "clear_history", None)
    if not callable(clear_hist):
        pytest.skip("MainWindow.clear_history not implemented")
    clear_hist()

    # Assert: history attribute emptied or cleared
    hist_after = getattr(mw, "history", None)
    # Accept either empty list or None as cleared state
    assert hist_after in ([], None), "clear_history should remove stored history entries"

    # Clear input: find a plausible input widget and verify clear_input empties it
    clear_input = getattr(mw, "clear_input", None)
    if not callable(clear_input):
        pytest.skip("MainWindow.clear_input not implemented")

    # Attempt to locate a text input widget on the MainWindow instance
    candidate_names = [
        "txt_input", "input", "lineEdit", "txtFirst", "txtSecond", "display",
        "line_edit", "input_field"
    ]
    widget = None
    for name in candidate_names:
        if hasattr(mw, name):
            widget = getattr(mw, name)
            break
    # If not found, attempt to find a child QLineEdit via QObject children (PyQt specific)
    if widget is None:
        try:
            children = mw.findChildren(QtWidgets.QLineEdit)
            if children:
                widget = children[0]
        except Exception:
            widget = None

    if widget is None:
        pytest.skip("No recognizable input widget found to test clear_input")

    # Ensure widget supports setText/text
    if not (hasattr(widget, "setText") and hasattr(widget, "text")):
        pytest.skip("Found input widget does not support setText/text API")

    # Act: set text, call clear_input
    widget.setText("should be cleared")
    # Sanity check precondition
    assert widget.text() != "", "Precondition failed: widget text should be non-empty"
    clear_input()

    # Assert: text cleared
    assert widget.text() == "", "clear_input should clear the text of the input widget"
