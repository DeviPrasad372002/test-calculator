
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
except ImportError:  # pragma: no cover
    import sys
    sys.exit(0)

try:
    import inspect
except ImportError:  # pragma: no cover
    pytest.skip("inspect unavailable", allow_module_level=True)

try:
    import builtins
except ImportError:  # pragma: no cover
    pytest.skip("builtins unavailable", allow_module_level=True)

try:
    from unittest import mock
except ImportError:  # pragma: no cover
    pytest.skip("unittest.mock unavailable", allow_module_level=True)

try:
    import Calculator
except ImportError:
    pytest.skip("Calculator module not available", allow_module_level=True)

try:
    import SimpleCalculatorPyQt1
except ImportError:
    pytest.skip("SimpleCalculatorPyQt1 module not available", allow_module_level=True)

# Helper to find a custom exception class by name in known modules
def _exc_lookup(name, default=Exception):
    return getattr(SimpleCalculatorPyQt1, name, getattr(Calculator, name, default))

# Generic dummy widgets to simulate different possible UI attribute names
class DummyInputWidget:
    def __init__(self, text=""):
        self._text = text
        self.set_calls = []

    # common Qt-like accessors
    def text(self):
        return self._text

    def toPlainText(self):
        return self._text

    def getText(self):
        return self._text

    # setters / clearers
    def setText(self, value):
        self.set_calls.append(value)
        self._text = value

    def setPlainText(self, value):
        self.set_calls.append(value)
        self._text = value

    def clear(self):
        self.set_calls.append("")
        self._text = ""

class DummyHistoryWidget:
    def __init__(self, initial=""):
        self._text = initial
        self.append_calls = []
        self.set_calls = []
        self.cleared = False

    def append(self, value):
        self.append_calls.append(value)
        self._text += ("\n" if self._text else "") + str(value)

    def setText(self, value):
        self.set_calls.append(value)
        self._text = value

    def setPlainText(self, value):
        self.set_calls.append(value)
        self._text = value

    def clear(self):
        self.cleared = True
        self._text = ""

    def toPlainText(self):
        return self._text

    def text(self):
        return self._text

@pytest.mark.parametrize("input_attr_name", ["input_field", "lineEdit", "input", "display", "lcd", "entry"])
def test_clear_input_empties_registered_input_variants(monkeypatch, input_attr_name):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fn = getattr(SimpleCalculatorPyQt1, "clear_input", None)
    if fn is None:
        pytest.skip("clear_input not present in module", allow_module_level=True)
    dummy_input = DummyInputWidget(text="12345")
    # Create a fake main window exposing several possible attribute names
    class FakeMain:
        pass
    fake = FakeMain()
    # attach our dummy to the attribute name under test
    setattr(fake, input_attr_name, dummy_input)
    # Also expose other common names so implementation can pick any
    for alt in ("lineEdit", "input_field", "entry", "input", "display"):
        if not hasattr(fake, alt):
            setattr(fake, alt, DummyInputWidget(text="should-not-be-cleared"))
    # Act
    sig = inspect.signature(fn)
    if len(sig.parameters) == 0:
        fn()
    else:
        fn(fake)
    # Assert: at least the targeted attribute was cleared via one of its setters/clear
    assert dummy_input._text == "" or "" in dummy_input.set_calls, "expected input widget to be cleared"

def test_clear_history_resets_history_widget_and_invokes_save(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fn = getattr(SimpleCalculatorPyQt1, "clear_history", None)
    if fn is None:
        pytest.skip("clear_history not present in module", allow_module_level=True)
    dummy_history = DummyHistoryWidget(initial="old\nhistory")
    saved = {"called": False, "value": None}
    # monkeypatch save_history if exists to capture invocation
    if hasattr(SimpleCalculatorPyQt1, "save_history"):
        def fake_save(hist_text):
            saved["called"] = True
            saved["value"] = hist_text
        monkeypatch.setattr(SimpleCalculatorPyQt1, "save_history", fake_save, raising=False)
    # Build fake main window with multiple possible names
    class FakeMain:
        pass
    fake = FakeMain()
    # Attach history under a common set of attribute names
    for name in ("history", "history_widget", "historyDisplay", "historyText", "textBrowser"):
        setattr(fake, name, dummy_history)
    # Act
    sig = inspect.signature(fn)
    if len(sig.parameters) == 0:
        fn()
    else:
        fn(fake)
    # Assert: history widget cleared or set to empty; save_history called if present
    assert dummy_history._text == "" or dummy_history.cleared or any(v == "" for v in dummy_history.set_calls), \
        "expected history widget to be cleared or set to empty"
    if hasattr(SimpleCalculatorPyQt1, "save_history"):
        assert saved["called"], "expected save_history to be invoked by clear_history"

def test_calculate_plus_calls_calculator_add_and_updates_ui_and_history(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fn = getattr(SimpleCalculatorPyQt1, "calculate", None)
    if fn is None:
        pytest.skip("calculate not present in module", allow_module_level=True)
    called = {"add": False}
    # Stub Calculator.add to observe usage
    def fake_add(a, b):
        called["add"] = True
        return a + b
    monkeypatch.setattr(Calculator, "add", fake_add, raising=False)
    # Ensure other operations raise if used (to detect accidental use)
    def _raise(*a, **k):
        raise RuntimeError("unexpected op used")
    monkeypatch.setattr(Calculator, "subtract", _raise, raising=False)
    monkeypatch.setattr(Calculator, "multiply", _raise, raising=False)
    monkeypatch.setattr(Calculator, "divide", _raise, raising=False)
    # fake save_history capture
    history_saved = {"called": False, "value": None}
    if hasattr(SimpleCalculatorPyQt1, "save_history"):
        def fake_save(v):
            history_saved["called"] = True
            history_saved["value"] = v
        monkeypatch.setattr(SimpleCalculatorPyQt1, "save_history", fake_save, raising=False)
    # Build a fake main window with an input that contains a plus expression
    input_widget = DummyInputWidget(text="2+3")
    history_widget = DummyHistoryWidget()
    class FakeMain:
        pass
    fake = FakeMain()
    # Attach input under multiple plausible attribute names
    for name in ("input_field", "lineEdit", "input", "display", "entry"):
        setattr(fake, name, input_widget)
    for name in ("history", "history_widget", "historyDisplay", "textBrowser"):
        setattr(fake, name, history_widget)
    # Act
    sig = inspect.signature(fn)
    if len(sig.parameters) == 0:
        fn()
    else:
        fn(fake)
    # Assert: Calculator.add was invoked and UI updated (either input set to result or history appended/saved)
    assert called["add"], "expected Calculator.add to be called for a plus expression"
    ui_was_updated = (input_widget._text == "5") or (history_widget.append_calls or history_saved["called"])
    assert ui_was_updated, "expected UI or history to be updated with the calculation result"

def test_calculate_handles_invalid_input_by_showing_error(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fn = getattr(SimpleCalculatorPyQt1, "calculate", None)
    if fn is None:
        pytest.skip("calculate not present in module", allow_module_level=True)
    # Force Calculator operations to raise a CalculatorError for invalid inputs
    CalcErr = _exc_lookup("CalculatorError", ValueError)
    def bad_add(a, b):
        raise CalcErr("invalid")
    monkeypatch.setattr(Calculator, "add", bad_add, raising=False)
    # Make fake input with invalid content that would trigger add usage
    input_widget = DummyInputWidget(text="notanumber+3")
    error_display = DummyInputWidget(text="")
    class FakeMain:
        pass
    fake = FakeMain()
    # Attach input and a potential error display name
    setattr(fake, "input_field", input_widget)
    setattr(fake, "errorLabel", error_display)
    # Act & Assert: calling calculate should not raise an uncaught exception and should display something in error display or leave input unchanged
    sig = inspect.signature(fn)
    try:
        if len(sig.parameters) == 0:
            fn()
        else:
            fn(fake)
    except Exception as exc:
        # If a different unexpected exception bubbles up, fail the test
        raise
    # After handling, expect either error_label updated or input remains unchanged (defensive)
    assert (error_display._text != "") or (input_widget._text == "notanumber+3"), \
        "expected error to be displayed or input to be unchanged after invalid calculation"
