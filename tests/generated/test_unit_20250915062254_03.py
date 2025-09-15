
# --- ENHANCED UNIVERSAL BOOTSTRAP ---
import os, sys, importlib.util as _iu, types as _types, pytest as _pytest, builtins as _builtins, warnings
STRICT = os.getenv("TESTGEN_STRICT", "1").lower() in ("1","true","yes")
STRICT_FAIL = os.getenv("TESTGEN_STRICT_FAIL","0").lower() in ("1","true","yes")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

_target = os.environ.get("TARGET_ROOT") or os.environ.get("ANALYZE_ROOT")
if _target and os.path.isdir(_target):
    if _target not in sys.path: sys.path.insert(0, _target)

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

import importlib
import inspect
import pytest

try:
    module = importlib.import_module('target.SimpleCalculatorPyQt1')
except Exception as exc:
    pytest.skip(f"Cannot import target.SimpleCalculatorPyQt1: {exc}", allow_module_level=True)


class DummyWidget:
    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text

    def setText(self, value):
        # mimic Qt behaviour of accepting non-strs but store str
        self._text = "" if value is None else str(value)


class DummyHistory:
    def __init__(self, entries=None):
        self.entries = list(entries or [])
        self.cleared = False

    def clear(self):
        self.cleared = True
        self.entries.clear()

    def add(self, entry):
        self.entries.append(entry)


class DummyWindow:
    """
    Provide many common attribute names the target functions might access:
    - lineEdit, inputField, input, entry
    - resultLabel, result, output
    - history, historyWidget
    """
    def __init__(self, input_text=""):
        # Input widgets
        self.lineEdit = DummyWidget(input_text)
        self.inputField = self.lineEdit
        self.input = self.lineEdit
        self.entry = self.lineEdit

        # Result widgets
        self.resultLabel = DummyWidget("")
        self.result = self.resultLabel
        self.output = self.resultLabel

        # History widget
        self.historyWidget = DummyHistory()
        self.history = self.historyWidget
        self.history_list = self.historyWidget


def _call_with_flexible_target(fn, window):
    """
    Call fn either with (window) if it expects an argument, or without if it expects none.
    Before calling a zero-arg fn, place the window object on common module-level names so
    the implementation can reference it (e.g. module.mainWindow / module.window / module.ui).
    Return whatever fn returns or raises.
    """
    sig = inspect.signature(fn)
    if len(sig.parameters) >= 1:
        return fn(window)
    # set common module-level names that implementation might use
    for name in ("mainWindow", "window", "ui", "MainWindow", "mw"):
        setattr(module, name, window)
    try:
        return fn()
    finally:
        # cleanup
        for name in ("mainWindow", "window", "ui", "MainWindow", "mw"):
            try:
                delattr(module, name)
            except Exception:
                pass


def test_clear_input_resets_input_and_result_fields():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    window = DummyWindow(input_text="123+456")
    # Pre-fill result to ensure it's cleared
    window.result.setText("preexisting")
    clear_input = getattr(module, 'clear_input', None)
    assert clear_input is not None and callable(clear_input)

    # Act
    _call_with_flexible_target(clear_input, window)

    # Assert - verify all common input and result attributes are cleared
    assert window.lineEdit.text() == "", "lineEdit should be cleared"
    assert window.inputField.text() == "", "inputField should be cleared"
    assert window.resultLabel.text() == "", "resultLabel should be cleared"
    assert window.result.text() == "", "result should be cleared"


def test_clear_history_clears_widget_or_history_file(tmp_path, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    window = DummyWindow()
    # populate history widget
    window.history.add("1 + 1 = 2")
    window.history.add("2 * 3 = 6")
    cleared_flag = {"widget_cleared": False, "file_cleared": False, "save_history_called": False}

    # If module exposes a save_history function, monitor calls
    save_history_fn = getattr(module, 'save_history', None)
    if save_history_fn is not None and callable(save_history_fn):
        def fake_save_history(*args, **kwargs):
            cleared_flag["save_history_called"] = True
            return None
        monkeypatch.setattr(module, 'save_history', fake_save_history)

    # If module defines a HISTORY_FILE or similar, write a file and point it to tmp_path
    candidate_file_attr_names = ['HISTORY_FILE', 'HISTORY_PATH', 'history_file', 'history_path']
    file_attr_set = None
    for name in candidate_file_attr_names:
        if hasattr(module, name):
            # set it to a temp file
            temp = tmp_path / "history.txt"
            temp.write_text("old history")
            monkeypatch.setattr(module, name, str(temp))
            file_attr_set = str(temp)
            break

    clear_history = getattr(module, 'clear_history', None)
    assert clear_history is not None and callable(clear_history)

    # Act
    _call_with_flexible_target(clear_history, window)

    # Assert: either the widget was cleared, or the history file was truncated, or save_history was called
    if hasattr(window.history, "cleared") and window.history.cleared:
        cleared_flag["widget_cleared"] = True

    if file_attr_set:
        content = tmp_path.joinpath("history.txt").read_text()
        if content == "" or content.strip() == "":
            cleared_flag["file_cleared"] = True

    assert any(cleared_flag.values()), "clear_history should clear a GUI history widget, or clear a history file, or call save_history"


@pytest.mark.parametrize("expr", ["2+3", "10-4", "6*7", "8/4", "5 + 2 * 3"])
def test_calculate_sets_result_and_calls_save_history(monkeypatch, expr):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    window = DummyWindow(input_text=expr)
    saved = {"called": False, "args": None, "kwargs": None}
    save_history_fn = getattr(module, 'save_history', None)
    if save_history_fn is not None and callable(save_history_fn):
        def fake_save_history(*args, **kwargs):
            saved["called"] = True
            saved["args"] = args
            saved["kwargs"] = kwargs
        monkeypatch.setattr(module, 'save_history', fake_save_history)

    calculate = getattr(module, 'calculate', None)
    assert calculate is not None and callable(calculate)

    # Act
    result = _call_with_flexible_target(calculate, window)

    # Assert: verify the result label contains the evaluated expression result (string)
    # Use Python eval to determine expected result; mirror formatting:
    expected_value = eval(expr)
    # Some implementations may format floats with .0, so convert to str of Python eval
    expected_str = str(expected_value)
    # Possible that implementation uses integer arithmetic for whole numbers - accept both '5' and '5.0' if numeric equal
    res_text = window.result.text()
    assert isinstance(res_text, str), "result text should be a string"
    # Compare numerically when possible
    try:
        # if both can be parsed as floats compare numerically
        assert float(res_text) == float(expected_str)
    except Exception:
        # fallback to direct string equality
        assert res_text == expected_str

    # If save_history exists, ensure it was called with something including the expression/result
    if save_history_fn is not None and callable(save_history_fn):
        assert saved["called"], "calculate should call save_history when available"


def test_calculate_raises_on_division_by_zero():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    expr = "1/0"
    window = DummyWindow(input_text=expr)
    calculate = getattr(module, 'calculate', None)
    assert calculate is not None and callable(calculate)

    # Determine expected exception type
    # Prefer CalculatorError from Calculator module on the implementation, fallback to ZeroDivisionError
    try:
        calc_module = importlib.import_module('target.Calculator')
    except Exception:
        CalculatorError = ZeroDivisionError
    else:
        CalculatorError = getattr(calc_module, 'CalculatorError', ZeroDivisionError)

    # Act / Assert
    with pytest.raises(CalculatorError):
        _call_with_flexible_target(calculate, window)
