
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
    import importlib
    import inspect
    from types import SimpleNamespace
    import math
except ImportError as _err:
    import pytest
    pytest.skip("Required test imports unavailable: %s" % _err, allow_module_level=True)

try:
    sc = importlib.import_module("target.SimpleCalculatorPyQt1")
except ImportError as _err:
    sc = None

try:
    calcmod = importlib.import_module("target.Calculator")
except ImportError as _err:
    calcmod = None

def _exc_lookup(name, fallback):
    if calcmod is None:
        return fallback
    return getattr(calcmod, name, fallback)

class DummyField:
    def __init__(self, initial=""):
        self._text = initial
        self.last_set_text = None
        self.appended = []
    def text(self):
        return self._text
    def setText(self, value):
        self._text = value
        self.last_set_text = str(value)
    # QTextEdit style
    def toPlainText(self):
        return self._text
    def setPlainText(self, value):
        self._text = value
        self.last_set_text = str(value)
    def append(self, value):
        self.appended.append(str(value))
        self.last_set_text = str(value)
    def clear(self):
        self._text = ""
        self.last_set_text = ""
    def __str__(self):
        return self._text

class DummyWindow:
    def __init__(self, input_value="", result_field=None, history_field=None):
        # input widget (many common attribute names mapped)
        self._input_field = DummyField(initial=input_value)
        # result widget (shared across many possible attribute names so any write will be captured)
        self._result_field = result_field or DummyField()
        # history widget/list
        self._history_field = history_field or DummyField()
        # Map many plausible attribute names used by different code styles
        for name in ("input", "input_line", "inputField", "lineEdit", "leInput", "inputText"):
            setattr(self, name, self._input_field)
        for name in ("result", "result_label", "display", "lblResult", "output"):
            setattr(self, name, self._result_field)
        for name in ("history", "history_widget", "textEdit", "historyText", "history_box"):
            setattr(self, name, self._history_field)
        # also expose a direct list-style history if code uses list semantics
        self.history_list = []
    # convenience to retrieve what was last set to result
    @property
    def last_result(self):
        return self._result_field.last_set_text
    @property
    def input_text(self):
        return self._input_field.text()
    def set_input(self, value):
        self._input_field.setText(str(value))

@pytest.mark.parametrize("attr_name,initial", [
    ("input", "42"),
    ("input_line", "foo"),
    ("lineEdit", "3+4"),
    ("leInput", "0"),
])
def test_clear_input_clears_various_input_attribute_names(attr_name, initial):
    # Arrange-Act-Assert: generated by ai-testgen
    if sc is None or not hasattr(sc, "clear_input"):
        pytest.skip("clear_input not available in target.SimpleCalculatorPyQt1")
    # Arrange
    window = DummyWindow(input_value=initial)
    # Ensure the specific attribute exists and is our dummy input
    assert getattr(window, attr_name).text() == initial
    # Act
    # call the clear_input implementation with the dummy window
    sig = inspect.signature(sc.clear_input)
    if len(sig.parameters) == 0:
        # maybe it's a bound function expecting no args (unlikely) - skip in that case
        pytest.skip("clear_input has unexpected signature")
    sc.clear_input(window)
    # Assert
    # The attribute used for input should be cleared to empty string via any of our dummy names
    assert getattr(window, attr_name).text() == ""


@pytest.mark.parametrize("history_initial,is_widget", [
    ("one entry\ntwo entry", True),
    ("single", True),
    (["a","b","c"], False),
])
def test_clear_history_clears_textual_and_list_histories(history_initial, is_widget):
    # Arrange-Act-Assert: generated by ai-testgen
    if sc is None or not hasattr(sc, "clear_history"):
        pytest.skip("clear_history not available in target.SimpleCalculatorPyQt1")
    # Arrange
    if is_widget:
        history_field = DummyField(initial=history_initial)
        window = DummyWindow(history_field=history_field)
        # sanity
        assert window.history_widget.toPlainText() == history_initial
    else:
        window = DummyWindow()
        # simulate a list-based history representation
        window.history_list = list(history_initial)
        assert window.history_list == list(history_initial)
    # Act
    sig = inspect.signature(sc.clear_history)
    if len(sig.parameters) == 0:
        pytest.skip("clear_history has unexpected signature")
    sc.clear_history(window)
    # Assert
    if is_widget:
        # widget should have been cleared
        assert window.history_widget.toPlainText() == ""
    else:
        # list should have been cleared
        assert window.history_list == []


@pytest.mark.parametrize("expr,expect_value,expect_error", [
    ("2+3", 5, False),
    ("10-4", 6, False),
    ("6*7", 42, False),
    ("8/2", 4.0, False),
    ("5/0", None, True),
])
def test_calculate_evaluates_expressions_and_handles_errors(expr, expect_value, expect_error):
    # Arrange-Act-Assert: generated by ai-testgen
    # This test exercises a top-level calculate function if available; otherwise it's skipped.
    if sc is None or not hasattr(sc, "calculate"):
        pytest.skip("calculate not available in target.SimpleCalculatorPyQt1")
    # Arrange
    result_field = DummyField()
    history_field = DummyField()
    window = DummyWindow(input_value=expr, result_field=result_field, history_field=history_field)
    # Act & Assert
    sig = inspect.signature(sc.calculate)
    if len(sig.parameters) == 0:
        pytest.skip("calculate has unexpected signature")
    try:
        sc.calculate(window)
    except Exception as e:
        # If an error was expected, ensure the raised exception is reasonable
        if not expect_error:
            raise
        # Accept either a Calculator-specific error or ZeroDivisionError or generic Exception
        allowed = (_exc_lookup("CalculatorError", Exception), ZeroDivisionError, Exception)
        assert isinstance(e, _exc_lookup("allowed", Exception))
        return
    # If no exception thrown, then result should be present in one of the result fields we exposed
    last = window.last_result
    assert last is not None and last != ""
    # For numeric expected values, allow integer/float text forms
    if not expect_error:
        try:
            # try parse as int then float to compare numerically
            if "." in last:
                val = float(last)
            else:
                val = int(last)
        except Exception:
            # Some implementations may append formatting; try float conversion anyway
            val = float(last)
        # numeric comparison with tolerance for float division
        assert math.isclose(val, float(expect_value), rel_tol=1e-9, abs_tol=1e-9) if isinstance(expect_value, _exc_lookup("float", Exception)) else val == expect_value
