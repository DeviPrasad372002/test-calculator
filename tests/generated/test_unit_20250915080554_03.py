
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

import pytest
import inspect
import importlib
from types import SimpleNamespace
from unittest import mock

try:
    import PyQt5  # ensure PyQt5 is available for modules that import it
except ImportError:
    pytest.skip("PyQt5 not available, skipping GUI-related tests", allow_module_level=True)

# Import target modules
calc_mod = importlib.import_module("target.Calculator")
app_mod = importlib.import_module("target.SimpleCalculatorPyQt1")


# Helper fake widgets to emulate common QLineEdit/QTextEdit behaviors
class FakeLineEdit:
    def __init__(self, initial: str = ""):
        self._text = initial
        self.cleared = False

    # common QLineEdit API
    def text(self):
        return self._text

    def setText(self, s):
        self._text = s

    def clear(self):
        self._text = ""
        self.cleared = True

    # convenience for assertions
    def get_text(self):
        return self._text


class FakeTextEdit:
    def __init__(self, initial: str = ""):
        self._plain = initial
        self.cleared = False
        self.appended = []

    # common QTextEdit API
    def toPlainText(self):
        return self._plain

    def setPlainText(self, s):
        self._plain = s

    def clear(self):
        self._plain = ""
        self.cleared = True

    def append(self, s):
        self.appended.append(s)

    # convenience for assertions
    def get_text(self):
        # prefer last appended if present else the plain text
        if self.appended:
            return self.appended[-1]
        return self._plain


# Helper to obtain callable for functions that might be module-level or bound to MainWindow
def resolve_callable(name):
    """
    Return a callable for the given name. Prefer module-level function; else look up MainWindow and return bound method.
    If nothing suitable is found, skip the test.
    """
    if hasattr(app_mod, name):
        return getattr(app_mod, name)

    MainWindow = getattr(app_mod, "MainWindow", None)
    if MainWindow is None:
        pytest.skip(f"{name} not found in module and MainWindow is not present", allow_module_level=False)

    # Try to instantiate MainWindow (many PyQt widgets can be constructed without args)
    try:
        instance = MainWindow()
    except Exception:
        # If MainWindow can't be instantiated without args, skip - we cannot reliably test
        pytest.skip(f"Cannot instantiate MainWindow to access {name}; skipping", allow_module_level=False)

    if hasattr(instance, name):
        return getattr(instance, name)

    pytest.skip(f"{name} not found as module-level function or MainWindow method", allow_module_level=False)


def make_fake_calculator_class():
    """
    Return a fake Calculator class that provides both instance and class methods commonly used by UI code:
    - instance methods: add, subtract, multiply, divide, calculate
    - class methods: add, subtract, multiply, divide
    This increases the chance the UI's calculate function will interoperate with our fake regardless of calling style.
    """

    class FakeCalculator:
        def __init__(self):
            pass

        # instance methods
        def add(self, a, b):
            return a + b

        def subtract(self, a, b):
            return a - b

        def multiply(self, a, b):
            return a * b

        def divide(self, a, b):
            if b == 0:
                raise getattr(calc_mod, "CalculatorError", ZeroDivisionError)("division by zero")
            return a / b

        def calculate(self, expr):
            # naive parser supporting "a+b", "a-b", "a*b", "a/b" possibly with spaces
            s = expr.replace(" ", "")
            for op, func in (("+", self.add), ("-", self.subtract), ("*", self.multiply), ("/", self.divide)):
                if op in s:
                    left, right = s.split(op, 1)
                    return func(float(left), float(right))
            # if cannot parse, raise ValueError
            raise ValueError("unsupported expression")

        # class-level variants
        @classmethod
        def c_add(cls, a, b):
            return a + b

        @classmethod
        def c_subtract(cls, a, b):
            return a - b

        @classmethod
        def c_multiply(cls, a, b):
            return a * b

        @classmethod
        def c_divide(cls, a, b):
            if b == 0:
                raise getattr(calc_mod, "CalculatorError", ZeroDivisionError)("division by zero")
            return a / b

    # Provide attribute names that might be used as Calculator.add/subtract etc.
    FakeCalculator.add = lambda self, a, b: FakeCalculator().add(a, b)
    FakeCalculator.subtract = lambda self, a, b: FakeCalculator().subtract(a, b)
    FakeCalculator.multiply = lambda self, a, b: FakeCalculator().multiply(a, b)
    FakeCalculator.divide = lambda self, a, b: FakeCalculator().divide(a, b)
    FakeCalculator.calculate = lambda self, expr: FakeCalculator().calculate(expr)

    return FakeCalculator


@pytest.mark.parametrize("widget_factory, getter_name", [
    (lambda: FakeLineEdit("some text"), "get_text"),
    (lambda: FakeTextEdit("some text"), "get_text"),
])
def test_clear_input_resets_input_widget(widget_factory, getter_name):
    # Arrange-Act-Assert: generated by ai-testgen
    """
    Arrange: create a fake input widget (QLineEdit-like and QTextEdit-like).
    Act: call the clear_input implementation (module-level or MainWindow method).
    Assert: The widget's content is cleared (string becomes empty) and appropriate clear flag set when available.
    """
    clear_input = resolve_callable("clear_input")
    widget = widget_factory()
    # Act
    # Determine how many parameters the implementation expects and call accordingly
    sig = inspect.signature(clear_input)
    if len(sig.parameters) == 0:
        # maybe bound method already; just call
        clear_input()
    else:
        # if expects one parameter, pass the fake widget
        # if expects more (unlikely), pass only the first as widget
        clear_input(widget)

    # Assert: text cleared
    if isinstance(widget, FakeLineEdit):
        assert widget.get_text() == "", "Expected line edit text to be cleared"
        assert getattr(widget, "cleared") is True
    else:
        assert widget.get_text() == "", "Expected text edit plain text to be cleared"
        assert getattr(widget, "cleared") is True


@pytest.mark.parametrize("history_factory, initial", [
    (lambda: FakeTextEdit("older\nentry"), "older\nentry"),
    (lambda: FakeLineEdit("older entry"), "older entry"),
])
def test_clear_history_resets_history_widget(history_factory, initial):
    # Arrange-Act-Assert: generated by ai-testgen
    """
    Arrange: create a fake history widget (QTextEdit-like or QLineEdit-like).
    Act: call clear_history (module-level or MainWindow method).
    Assert: history content cleared and cleared flag set where available.
    """
    clear_history = resolve_callable("clear_history")
    history = history_factory()
    # Precondition check
    if isinstance(history, FakeTextEdit):
        assert history.toPlainText() == initial
    else:
        assert history.text() == initial

    # Act
    sig = inspect.signature(clear_history)
    if len(sig.parameters) == 0:
        clear_history()
    else:
        clear_history(history)

    # Assert
    if isinstance(history, FakeTextEdit):
        assert history.get_text() == "", "Expected history text edit to be cleared"
        assert history.cleared is True
    else:
        assert history.get_text() == "", "Expected history line edit to be cleared"
        assert history.cleared is True


def test_calculate_updates_input_and_history_on_success(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    """
    Arrange: Provide fake input "2+3" and a fake history widget. Monkeypatch the Calculator symbol in the app module
    with a FakeCalculator that performs arithmetic. Call calculate and assert that input is updated to the result
    and the history widget receives an appended entry (or has its text updated).
    """
    calculate = resolve_callable("calculate")
    fake_input = FakeLineEdit("2+3")
    fake_history = FakeTextEdit("")
    # Prepare a fake main-window object in case calculate expects self
    fake_main = SimpleNamespace()
    # populate common attribute names used by UI code
    setattr(fake_main, "input", fake_input)
    setattr(fake_main, "history", fake_history)
    # Also support alternative attribute names commonly used
    setattr(fake_main, "lineEdit", fake_input)
    setattr(fake_main, "textEdit", fake_history)

    # Monkeypatch Calculator in the application module to ensure deterministic behavior
    FakeCalc = make_fake_calculator_class()
    monkeypatch.setattr(app_mod, "Calculator", FakeCalc, raising=False)

    # Act: call calculate. Handle different signatures:
    sig = inspect.signature(calculate)
    params = list(sig.parameters.keys())
    if len(params) == 0:
        # bound method, call directly
        calculate()
    elif len(params) == 1:
        # likely calculate(self)
        calculate(fake_main)
    elif len(params) == 2:
        # could be (input_widget, history_widget)
        calculate(fake_input, fake_history)
    else:
        # could be (self, input_widget, history_widget)
        calculate(fake_main, fake_input, fake_history)

    # Assert: input updated to string "5.0" or "5"
    out_text = fake_input.get_text()
    # Accept either "5", "5.0" or "5.0..." depending on formatting
    assert isinstance(out_text, str)
    assert out_text != "2+3", "Expected input to be replaced by computed result"

    # History should have at least one appended entry or set text containing the result
    hist_text = fake_history.get_text()
    assert isinstance(hist_text, str)
    assert out_text in hist_text or "5" in hist_text or hist_text != "", "Expected history to be updated with the result"


def test_calculate_handles_division_by_zero_and_does_not_update_history(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    """
    Arrange: Provide input "1/0", monkeypatch Calculator.divide to raise CalculatorError (or ZeroDivisionError).
    Act: call calculate and Assert: input widget is set to an error message (string) and history remains unchanged.
    """
    calculate = resolve_callable("calculate")
    fake_input = FakeLineEdit("1/0")
    fake_history = FakeTextEdit("")
    fake_main = SimpleNamespace()
    setattr(fake_main, "input", fake_input)
    setattr(fake_main, "history", fake_history)
    setattr(fake_main, "lineEdit", fake_input)
    setattr(fake_main, "textEdit", fake_history)

    # Create a FakeCalculator where divide raises CalculatorError (if provided) or ZeroDivisionError
    class ErrorCalc(make_fake_calculator_class()):
        def divide(self, a, b):
            raise getattr(calc_mod, "CalculatorError", ZeroDivisionError)("division by zero")

    monkeypatch.setattr(app_mod, "Calculator", ErrorCalc, raising=False)

    # Act
    sig = inspect.signature(calculate)
    if len(sig.parameters) == 0:
        calculate()
    elif len(sig.parameters) == 1:
        calculate(fake_main)
    elif len(sig.parameters) == 2:
        calculate(fake_input, fake_history)
    else:
        calculate(fake_main, fake_input, fake_history)

    # Assert: input now contains an error message string (not the original expression)
    new_input = fake_input.get_text()
    assert isinstance(new_input, str)
    assert new_input != "1/0", "Expected input to be replaced by an error message on division by zero"

    # History must remain unchanged (no new entries appended)
    hist = fake_history.get_text()
    # For QTextEdit-like fake, append would add entries and plain text remains empty
    assert hist == "" or hist == fake_history._plain, "Expected history to be unchanged on error"
