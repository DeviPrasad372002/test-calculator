
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

import os
import re
import pytest

# Ensure headless Qt if PyQt5 is used by the application
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import PyQt5  # guard third-party import as requested
except ImportError:
    pytest.skip("PyQt5 is required for these end-to-end tests", allow_module_level=True)

try:
    import Calculator as calc
    import SimpleCalculatorPyQt1 as sc
except ImportError:
    pytest.skip("Required application modules (Calculator, SimpleCalculatorPyQt1) are not importable", allow_module_level=True)


def _instantiate_calculator():
    """
    Try to instantiate a Calculator object from the Calculator module.
    If not available, return None.
    """
    C = getattr(calc, "Calculator", None)
    if C is None:
        return None
    return C()


def _call_calculate_expression(expression):
    """
    Black-box attempt to evaluate a simple binary expression using the public API.
    Supports expressions like '2+3', ' 10 -4', '5* 6', '8/2'.
    Preference order:
      1. If Calculator instance has a 'calculate' method, use it.
      2. Else, try to parse and call module-level add/subtract/multiply/divide functions.
    """
    # Attempt 1: use Calculator.calculate if present
    inst = _instantiate_calculator()
    if inst is not None and hasattr(inst, "calculate"):
        return inst.calculate(expression), inst

    # Attempt 2: parse and call module-level arithmetic functions
    m = re.match(r"^\s*([-+]?\d+(?:\.\d+)?)\s*([\+\-\*/])\s*([-+]?\d+(?:\.\d+)?)\s*$", expression)
    if not m:
        raise ValueError("Expression format not supported by test helper: %r" % expression)
    a_str, op, b_str = m.group(1), m.group(2), m.group(3)
    a = float(a_str) if ('.' in a_str) else int(a_str)
    b = float(b_str) if ('.' in b_str) else int(b_str)

    if op == "+":
        fn = getattr(calc, "add", None)
        if fn is None:
            raise pytest.SkipTest("No add function available in Calculator module")
        return fn(a, b), None
    if op == "-":
        fn = getattr(calc, "subtract", None)
        if fn is None:
            raise pytest.SkipTest("No subtract function available in Calculator module")
        return fn(a, b), None
    if op == "*":
        fn = getattr(calc, "multiply", None)
        if fn is None:
            raise pytest.SkipTest("No multiply function available in Calculator module")
        return fn(a, b), None
    if op == "/":
        fn = getattr(calc, "divide", None)
        if fn is None:
            raise pytest.SkipTest("No divide function available in Calculator module")
        return fn(a, b), None

    raise ValueError("Unsupported operator in expression: %r" % expression)


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("2+3", 5),
        ("10 - 4", 6),
        ("5*6", 30),
        ("8/2", 4),
    ],
)
def test_calculate_parametrized_basic_operations(expression, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # (No global state required beyond module-level; instantiate is done by helper)

    # Act
    result, inst = _call_calculate_expression(expression)

    # Assert: concrete type and numeric equality
    assert isinstance(result, (int, float)), "Result should be numeric"
    # Normalize floats that are effectively integers
    if isinstance(result, float) and abs(result - round(result)) < 1e-9:
        result = int(round(result))
    assert result == expected

    # If a Calculator instance is available, assert side-effect on its history (state change)
    if inst is not None:
        # Arrange (history snapshot)
        hist = getattr(inst, "history", None)
        assert hist is not None, "Calculator instance should expose a 'history' attribute"
        # Assert: last history entry exists and records the operation in string form
        assert len(hist) >= 1
        last = hist[-1]
        assert isinstance(last, str)
        # The representation should contain the operands and the result somewhere
        assert re.search(r"\b2\b|\b10\b|\b5\b|\b8\b", last) or re.search(r"\b\d", last)
        assert str(expected) in last


def test_divide_by_zero_raises_defined_exception():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Prefer instance divide method, else module-level divide
    inst = _instantiate_calculator()
    calc_error = getattr(calc, "CalculatorError", ZeroDivisionError)

    # Act/Assert
    if inst is not None and hasattr(inst, "divide"):
        with pytest.raises(calc_error):
            inst.divide(5, 0)
    else:
        divide_fn = getattr(calc, "divide", None)
        if divide_fn is None:
            pytest.skip("No divide API available to test divide-by-zero behavior")
        with pytest.raises(calc_error):
            divide_fn(5, 0)


def test_clear_history_clears_stored_history_state():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    inst = _instantiate_calculator()
    if inst is None:
        pytest.skip("Calculator instance is required for this clear-history test")

    # Ensure there's at least one entry to clear
    # Act: perform an operation to populate history
    if hasattr(inst, "calculate"):
        inst.calculate("1+1")
    else:
        # Fall back to module-level add
        add_fn = getattr(calc, "add", None)
        if add_fn is None:
            pytest.skip("No API available to add history entry for test")
        # If history exists, append a synthetic entry if possible
        hist = getattr(inst, "history", None)
        if hist is None:
            pytest.skip("Calculator instance has no history attribute to test clear_history")
        hist.append("1+1=2")

    # Pre-assert: history has at least one entry
    hist = getattr(inst, "history", None)
    assert hist is not None
    assert len(hist) >= 1

    # Act: call clear_history via instance method if present, else module-level function
    if hasattr(inst, "clear_history"):
        inst.clear_history()
    else:
        clear_fn = getattr(sc, "clear_history", None)
        if clear_fn is None:
            pytest.skip("No clear_history API available")
        # try both signatures: no-arg, or expecting the instance
        try:
            clear_fn()
        except TypeError:
            clear_fn(inst)

    # Assert: history emptied
    hist_after = getattr(inst, "history", None)
    assert hist_after is not None
    assert len(hist_after) == 0


def test_clear_input_resets_input_widget(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # This test exercises the GUI-level clear_input behavior in a black-box manner.
    MainWindow = getattr(sc, "MainWindow", None)
    clear_input_fn = getattr(sc, "clear_input", None)

    if MainWindow is None and clear_input_fn is None:
        pytest.skip("Neither MainWindow nor clear_input API available for GUI input clearing test")

    # Create a QApplication for widget instantiation if necessary
    try:
        from PyQt5.QtWidgets import QApplication, QLineEdit
    except Exception:
        pytest.skip("PyQt5.QtWidgets unavailable; cannot test GUI input clearing")

    app = QApplication.instance() or QApplication([])

    # Arrange: instantiate window if MainWindow exists, otherwise use a lightweight fake with expected attribute names
    if MainWindow is not None:
        win = MainWindow()
    else:
        # Synthesize a minimal object with a QLineEdit-like API
        win = type("FakeWin", (), {})()
        win.display = QLineEdit()

    # Try to locate the text input widget: common names used in simple calculators
    candidate_names = ["display", "lineEdit", "input", "input_field", "txtInput", "leInput"]
    text_widget = None
    for name in candidate_names:
        if hasattr(win, name):
            widget = getattr(win, name)
            # Heuristic: QLineEdit-like object must have text() and setText()
            if hasattr(widget, "setText") and hasattr(widget, "text"):
                text_widget = widget
                break

    # If not found, try to inspect attributes looking for a QLineEdit instance
    if text_widget is None:
        for attr in dir(win):
            widget = getattr(win, attr)
            if hasattr(widget, "setText") and hasattr(widget, "text"):
                text_widget = widget
                break

    if text_widget is None:
        pytest.skip("No QLineEdit-like input widget found on MainWindow for clear_input test")

    # Set known text
    text_widget.setText("  12345  ")
    assert text_widget.text().strip() == "12345" or "12345" in text_widget.text()

    # Act: invoke clear_input via module-level function if present, else try to call window method
    if clear_input_fn is not None:
        # Try call signatures: (win) or no-arg
        try:
            clear_input_fn(win)
        except TypeError:
            clear_input_fn()
    elif hasattr(win, "clear_input"):
        getattr(win, "clear_input")()
    else:
        pytest.skip("No callable clear_input API found to exercise")

    # Assert: the text widget is now empty or whitespace-only
    remaining = text_widget.text()
    assert isinstance(remaining, str)
    assert remaining.strip() == ""
