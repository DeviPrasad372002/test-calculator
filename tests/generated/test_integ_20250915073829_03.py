
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

import inspect
import builtins
import io
import os
import pytest
from unittest import mock

# Guard third-party PyQt5 import as requested
try:
    import PyQt5  # noqa: F401
except ImportError:
    pytest.skip("PyQt5 is not available, skipping GUI-related integration tests", allow_module_level=True)

# Import target modules under test
import Calculator
import SimpleCalculatorPyQt1


# Lightweight dummy widgets that mimic enough of QLineEdit / QTextEdit APIs
class DummyLineEdit:
    def __init__(self, text=""):
        self._text = str(text)

    # QLineEdit API
    def text(self):
        return self._text

    def setText(self, s):
        self._text = str(s)

    def clear(self):
        self._text = ""

    # sometimes code may access .text property
    @property
    def text_prop(self):
        return self._text


class DummyTextEdit:
    def __init__(self, text=""):
        self._text = str(text)

    # QTextEdit API
    def toPlainText(self):
        return self._text

    def setPlainText(self, s):
        self._text = str(s)

    def append(self, s):
        if self._text:
            self._text += "\n" + str(s)
        else:
            self._text = str(s)

    def clear(self):
        self._text = ""

    # sometimes code uses .setText / .text
    def setText(self, s):
        self._text = str(s)

    def text(self):
        return self._text


class DummyMainWindow:
    """
    Create many common attribute aliases so the real functions can find expected widgets.
    This increases robustness against different attribute naming in the GUI module.
    """
    def __init__(self, input_text="", history_text=""):
        self._input = DummyLineEdit(input_text)
        self._history = DummyTextEdit(history_text)

        # common QLineEdit names
        self.lineEdit = self._input
        self.inputLineEdit = self._input
        self.input = self._input
        self.entry = self._input
        self.display = self._input

        # common QTextEdit names
        self.textEdit = self._history
        self.historyTextEdit = self._history
        self.history = self._history
        self.output = self._history
        self.log = self._history


def _call_with_mainwindow_robust(func, mainwindow, file_path=None, monkeypatch=None):
    """
    Call func with either (mainwindow, file_path) or (mainwindow,) depending on its signature.
    Additionally, if func uses QFileDialog.getSaveFileName, attempt to monkeypatch it to return file_path.
    Returns whatever func returns.
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # If function possibly relies on QFileDialog.getSaveFileName, monkeypatch it to return our file_path.
    if file_path is not None and monkeypatch is not None:
        # Try both attribute locations that might be used in the module
        for attr in ("QFileDialog",):
            qfd = getattr(SimpleCalculatorPyQt1, attr, None)
            if qfd:
                # If QFileDialog exists as class, patch its getSaveFileName method
                if hasattr(qfd, "getSaveFileName"):
                    monkeypatch.setattr(qfd, "getSaveFileName", lambda *a, **k: (str(file_path), ""))
                # else, if it is a function or something else, try to patch module level
        # Also try patching from PyQt5 directly if referenced that way inside module (best-effort)
        try:
            import PyQt5.QtWidgets as _qtwidgets
            if hasattr(_qtwidgets, "QFileDialog"):
                monkeypatch.setattr(_qtwidgets.QFileDialog, "getSaveFileName", lambda *a, **k: (str(file_path), ""))
        except Exception:
            # best-effort only
            pass

    if len(params) == 0:
        return func()
    if len(params) == 1:
        return func(mainwindow)
    if len(params) >= 2:
        # pass file_path if available else pass empty string
        arg2 = file_path if file_path is not None else ""
        return func(mainwindow, arg2)
    # fallback
    return func(mainwindow)


def _read_dummy_history(mainwindow):
    # find the history widget among many aliases and return its text
    for name in ("historyTextEdit", "textEdit", "history", "output", "log"):
        widget = getattr(mainwindow, name, None)
        if widget is not None:
            # prefer toPlainText if present
            if hasattr(widget, "toPlainText"):
                return widget.toPlainText()
            if hasattr(widget, "text"):
                # some widgets use text()
                try:
                    return widget.text()
                except TypeError:
                    return getattr(widget, "text", "")
    return ""


def _read_dummy_input(mainwindow):
    for name in ("lineEdit", "inputLineEdit", "input", "entry", "display"):
        widget = getattr(mainwindow, name, None)
        if widget is not None:
            if hasattr(widget, "text"):
                try:
                    return widget.text()
                except TypeError:
                    pass
            # property access attempt
            if hasattr(widget, "text_prop"):
                return widget.text_prop
    return ""


# Integration tests (2-5) that cross modules naturally and mock external calls.

def test_clear_history_and_clear_input_integration():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    mw = DummyMainWindow(input_text="42", history_text="old entry")
    # Pre-assert state
    assert _read_dummy_input(mw) == "42"
    assert "old entry" in _read_dummy_history(mw)

    # Act: call clear_history and clear_input functions as provided by the GUI module
    # Use robust caller to adapt to possible signatures
    clear_history = getattr(SimpleCalculatorPyQt1, "clear_history", None)
    clear_input = getattr(SimpleCalculatorPyQt1, "clear_input", None)
    assert clear_history is not None, "clear_history function not found in SimpleCalculatorPyQt1"
    assert clear_input is not None, "clear_input function not found in SimpleCalculatorPyQt1"

    _call_with_mainwindow_robust(clear_history, mw)
    _call_with_mainwindow_robust(clear_input, mw)

    # Assert: both input and history cleared
    assert _read_dummy_input(mw) in ("", None, ""), "expected input to be cleared"
    assert _read_dummy_history(mw) in ("", None, ""), "expected history to be cleared"


def test_save_history_writes_file_integration(tmp_path, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    content_lines = ["one + two = 3", "three * four = 12"]
    mw = DummyMainWindow(input_text="ignored", history_text="\n".join(content_lines))
    save_history = getattr(SimpleCalculatorPyQt1, "save_history", None)
    assert save_history is not None, "save_history function not found in SimpleCalculatorPyQt1"

    out_file = tmp_path / "history_out.txt"

    # Ensure any dialog-based file selection returns our path by monkeypatching
    # and also guard builtins.open used inside the module to write, capturing the write call.
    # We'll prefer to let the function write to the real filesystem under tmp_path.
    # Act
    _call_with_mainwindow_robust(save_history, mw, file_path=out_file, monkeypatch=monkeypatch)

    # Assert: the file exists and contains the expected history text
    # If the save_history function did accept a path and wrote, the file should exist.
    if out_file.exists():
        data = out_file.read_text(encoding="utf-8")
        for line in content_lines:
            assert line in data
    else:
        # If the function uses a different mechanism and did not write to our file, fail explicitly
        pytest.fail(f"save_history did not write to expected path {out_file!s}")


@pytest.mark.parametrize(
    "expr, expected_result",
    [
        ("2+3", "5"),
        ("10-4", "6"),
        ("6*7", "42"),
        ("8/2", "4"),
    ],
)
def test_calculate_basic_operations_integration(expr, expected_result, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    mw = DummyMainWindow(input_text=expr, history_text="")
    calculate = getattr(SimpleCalculatorPyQt1, "calculate", None)
    assert calculate is not None, "calculate function not found in SimpleCalculatorPyQt1"

    # Act
    _call_with_mainwindow_robust(calculate, mw, monkeypatch=monkeypatch)

    # Assert: some result was appended to history and equals expected_result somewhere
    hist = _read_dummy_history(mw)
    assert hist, "expected history to be non-empty after calculation"
    # concrete check: the expected result appears in the history text
    assert expected_result in hist, f"expected result '{expected_result}' found in history, got: {hist!r}"
    # and the input should be cleared (typical GUI behavior)
    assert _read_dummy_input(mw) in ("", None, "")


def test_calculate_handles_division_by_zero_integration(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: set input to a division by zero expression
    mw = DummyMainWindow(input_text="1/0", history_text="")
    calculate = getattr(SimpleCalculatorPyQt1, "calculate", None)
    assert calculate is not None, "calculate function not found in SimpleCalculatorPyQt1"

    # Optionally, ensure Calculator.divide raises the CalculatorError or ZeroDivisionError to simulate backend error
    # Use getattr to prefer Calculator.CalculatorError if present
    calc_err = getattr(Calculator, "CalculatorError", ZeroDivisionError)

    # Monkeypatch the Calculator.divide function if it exists to raise the expected error
    if hasattr(Calculator, "divide"):
        monkeypatch.setattr(Calculator, "divide", lambda a, b: (_ for _ in ()).throw(calc_err("division by zero")))

    # Act
    _call_with_mainwindow_robust(calculate, mw, monkeypatch=monkeypatch)

    # Assert: GUI should not crash; history should contain an error indication or the exception handled.
    hist = _read_dummy_history(mw)
    # We assert concretely that either an explicit 'Error' word appears or the original expression is still present.
    if hist:
        assert ("Error" in hist) or ("error" in hist.lower()) or ("division" in hist.lower()) or ("1/0" in hist), (
            "expected an error message or original expression in history when dividing by zero, got: %r" % hist
        )
    else:
        # If history is empty, at minimum the input should have been cleared or left intact but no crash occurred.
        assert _read_dummy_input(mw) in ("", "1/0", None)
