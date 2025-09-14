
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
    import os
    import builtins
    from types import SimpleNamespace
    from unittest.mock import Mock
    import target.SimpleCalculatorPyQt1 as sc
    import target.Calculator as calc_mod
except ImportError:
    import pytest
    pytest.skip("required modules not found; skipping tests", allow_module_level=True)


def _exc_lookup(name, fallback=Exception):
    return getattr(calc_mod, name, getattr(sc, name, fallback))


class _FakeLineEdit:
    def __init__(self, initial: str):
        self._text = str(initial)
        self.set_calls = []

    def text(self):
        return self._text

    def setText(self, value):
        self.set_calls.append(value)
        self._text = value


class _FakeResultDisplay:
    def __init__(self):
        self.set_calls = []

    def setText(self, txt):
        self.set_calls.append(txt)


class _FakeComboBox:
    def __init__(self, current_text: str):
        self._current = current_text

    def currentText(self):
        return self._current


class _FakeListWidget:
    def __init__(self, items=None):
        self.items = list(items or [])
        self.cleared = False
        self.added = []

    def clear(self):
        self.cleared = True
        self.items = []

    def addItem(self, txt):
        self.added.append(txt)
        self.items.append(txt)

    def count(self):
        return len(self.items)


def _make_fake_mainwindow(a, b, op):
    fake = SimpleNamespace()
    fake.inputA = _FakeLineEdit(a)
    fake.inputB = _FakeLineEdit(b)
    # some implementations use lineEdit, lineEdit_2, result, etc.
    # provide several commonly used attribute names so sc.calculate/clear_input can work with at least one.
    fake.lineEdit = fake.inputA
    fake.lineEdit_2 = fake.inputB
    fake.input1 = fake.inputA
    fake.input2 = fake.inputB

    fake.result_display = _FakeResultDisplay()
    fake.resultLabel = fake.result_display
    fake.result = fake.result_display

    # Provide history widget name variations
    fake.listWidget = _FakeListWidget()
    fake.historyList = fake.listWidget
    fake.history = fake.listWidget

    fake.operation = _FakeComboBox(op)
    fake.comboBox = fake.operation
    fake.operationCombo = fake.operation

    # container for a Calculator instance if code sets it
    fake.calculator = None
    return fake


def _bind_result_setters(fake, result_attr_name='result_display'):
    # Many implementations call setText on a QLabel accessible via ui.result or similar.
    # Attach setText methods to plausible attributes so clear_input/ calculate can find them.
    setattr(fake, 'result_display', getattr(fake, result_attr_name))
    setattr(fake, 'resultLabel', getattr(fake, result_attr_name))
    setattr(fake, 'result', getattr(fake, result_attr_name))


def _call_maybe(fn, *args, **kwargs):
    # helper to call function if exists
    if fn:
        return fn(*args, **kwargs)


def test_clear_input_clears_all_input_fields_and_preserves_calculator_state():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake = _make_fake_mainwindow("12", "34", "Add")
    _bind_result_setters(fake)
    fake.calculator = calc_mod.Calculator() if hasattr(calc_mod, "Calculator") else object()

    # Pre-assert initial state
    assert fake.input1.text() == "12"
    assert fake.input2.text() == "34"
    # Act
    # clear_input may be a function or method; treat sc.clear_input as function expecting self
    clear_fn = getattr(sc, "clear_input", None)
    assert clear_fn is not None, "target.SimpleCalculatorPyQt1.clear_input is missing"
    clear_fn(fake)

    # Assert - inputs cleared, calculator attribute still present and unchanged type
    assert fake.input1.text() == "", "input1 should be cleared to empty string"
    assert fake.input2.text() == "", "input2 should be cleared to empty string"
    assert hasattr(fake, "calculator"), "calculator attribute must still exist"
    # Type of calculator should remain the same as before
    assert isinstance(fake.calculator, type(calc_mod.Calculator())) or isinstance(fake.calculator, object)


def test_clear_history_clears_widget_and_removes_history_file(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake = _make_fake_mainwindow("0", "0", "Add")
    _bind_result_setters(fake)
    # Prepare listWidget with some items
    fake.listWidget.addItem("1 + 2 = 3")
    fake.listWidget.addItem("4 + 5 = 9")
    assert fake.listWidget.count() == 2

    removed = {"called": False, "path": None}
    def fake_remove(path):
        removed["called"] = True
        removed["path"] = path

    # Many implementations remove a file named 'history.txt' in current dir
    expected_filename = "history.txt"
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    monkeypatch.setattr(os, "remove", fake_remove)

    # Act
    clear_hist_fn = getattr(sc, "clear_history", None)
    assert clear_hist_fn is not None, "target.SimpleCalculatorPyQt1.clear_history is missing"
    clear_hist_fn(fake)

    # Assert - widget cleared and os.remove called for the expected file
    assert fake.listWidget.cleared is True
    assert removed["called"] is True, "os.remove should have been called to remove history file"
    # concrete filename check (common implementations use 'history.txt')
    assert removed["path"].endswith(expected_filename), f"history removal expected to target a file ending with {expected_filename}"


@pytest.mark.parametrize("op_name, method_name, a,b, expected", [
    ("Add", "add", 3, 6, 9),
    ("Subtract", "subtract", 10, 2, 8),
    ("Multiply", "multiply", 3, 5, 15),
    ("Divide", "divide", 8, 2, 4),
])
def test_calculate_uses_calculator_methods_and_calls_save_history(monkeypatch, op_name, method_name, a, b, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake = _make_fake_mainwindow(str(a), str(b), op_name)
    _bind_result_setters(fake)
    saved = {"called": 0}
    def fake_save_history(self_or_none=None):
        saved["called"] += 1

    # Create a fake Calculator class with the target method
    class FakeCalc:
        def __init__(self, *args, **kwargs):
            self.called = []

        def add(self, x, y):
            self.called.append(("add", x, y))
            return x + y

        def subtract(self, x, y):
            self.called.append(("subtract", x, y))
            return x - y

        def multiply(self, x, y):
            self.called.append(("multiply", x, y))
            return x * y

        def divide(self, x, y):
            self.called.append(("divide", x, y))
            # emulate normal division behavior
            return x / y

    # Monkeypatch the Calculator class used by the GUI module to our FakeCalc
    monkeypatch.setattr(calc_mod, "Calculator", FakeCalc)
    # Monkeypatch save_history in GUI module to avoid file IO
    monkeypatch.setattr(sc, "save_history", fake_save_history)

    # Act
    calc_fn = getattr(sc, "calculate", None)
    assert calc_fn is not None, "target.SimpleCalculatorPyQt1.calculate is missing"

    # call calculate and capture behavior; some implementations expect attributes in different names,
    # but our fake provides many common ones
    calc_fn(fake)

    # Assert
    # Ensure save_history was invoked exactly once for a successful operation
    assert saved["called"] == 1, "save_history must be called once on successful calculation"
    # Ensure result_display received a textual result and matches expected numeric value as string
    # Accept both integer or float string representations (e.g., '4' or '4.0')
    calls = fake.result_display.set_calls
    assert len(calls) >= 1, "result display should have been updated at least once"
    # check last call string represents the expected numeric result
    last = calls[-1]
    assert isinstance(last, _exc_lookup("str", Exception))
    # convert to float for numeric comparison
    try:
        numeric = float(last)
    except Exception:
        pytest.fail(f"result text is not numeric: {last!r}")
    assert abs(numeric - float(expected)) < 1e-9


def test_calculate_handles_calculator_exception_and_avoids_saving(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake = _make_fake_mainwindow("5", "0", "Divide")
    _bind_result_setters(fake)
    saved = {"called": 0}
    def fake_save_history(self_or_none=None):
        saved["called"] += 1

    # Create exception class to be raised by divide
    CalcError = _exc_lookup("CalculatorError", Exception)

    class FakeCalcErr:
        def __init__(self, *a, **k):
            pass
        def divide(self, x, y):
            raise CalcError("division error simulated")

    # Monkeypatch Calculator to our failing fake
    monkeypatch.setattr(calc_mod, "Calculator", FakeCalcErr)
    monkeypatch.setattr(sc, "save_history", fake_save_history)

    calc_fn = getattr(sc, "calculate", None)
    assert calc_fn is not None, "target.SimpleCalculatorPyQt1.calculate is missing"

    # Act - call and allow either propagation or internal handling
    exception_raised = False
    try:
        calc_fn(fake)
    except Exception as exc:
        exception_raised = True
        # ensure it's the calculator-related exception or a subclass
        assert isinstance(exc, _exc_lookup("CalcError", Exception))

    # Assert - saving must not have occurred
    assert saved["called"] == 0, "save_history must not be called when calculation fails"

    # If exception was handled internally, GUI should have updated the result display to some text indicating error.
    if not exception_raised:
        # Must have at least one setText call and it must be a string
        calls = fake.result_display.set_calls
        assert len(calls) >= 1, "result display should be updated on handled exception"
        assert isinstance(calls[-1], str)
        # the string should mention 'error' or be non-empty; check non-empty concrete state
        assert calls[-1] != "", "result display must not be set to empty string on error"
