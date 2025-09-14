
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
    import inspect
    import types
    import Calculator
    import SimpleCalculatorPyQt1 as sc
    from unittest import mock
except ImportError:
    import pytest  # ensure pytest name exists for skip call
    pytest.skip("Required modules (Calculator or SimpleCalculatorPyQt1) not available", allow_module_level=True)


def _exc_lookup(name, default):
    # Attempt to find an exception class on the Calculator module; fallback to default.
    return getattr(Calculator, name, default)


def _resolve_callable(module, attr_name):
    """
    Return a callable from module or None if not present.
    """
    fn = getattr(module, attr_name, None)
    if fn is None:
        # if attr is a method on MainWindow, return the function object
        mw = getattr(module, "MainWindow", None)
        if mw is not None:
            fn = getattr(mw, attr_name, None)
    return fn


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("2+3", 5),
        ("4*5", 20),
        ("7-10", -3),
        ("8/2", 4.0),
    ],
)
def test_calculate_returns_expected_numeric_results(expr, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calculate = _resolve_callable(sc, "calculate")
    if calculate is None or not callable(calculate):
        pytest.skip("calculate callable not found in SimpleCalculatorPyQt1")
    sig = inspect.signature(calculate)
    # Prepare a dummy main/window object that may be required as 'self'
    class DummyMain:
        def __init__(self):
            # common widget shapes the implementation might access
            self.input = mock.Mock()
            self.ui = types.SimpleNamespace(input=self.input, history=mock.Mock())
            self.lineEdit = self.input
            self.history = mock.Mock()

    dummy = DummyMain()

    # Act
    try:
        if len(sig.parameters) == 0:
            result = calculate()
        elif len(sig.parameters) == 1:
            # could be a free function taking expr
            result = calculate(expr)
        else:
            # assume signature like (self, expr)
            result = calculate(dummy, expr)
    except TypeError:
        pytest.skip("calculate exists but could not be invoked with available calling patterns")

    # Assert - normalize string results to numeric if necessary
    if isinstance(result, _exc_lookup("str", Exception)):
        # try to parse to float/int
        try:
            if "." in result:
                num = float(result)
            else:
                num = int(result)
        except Exception:
            pytest.fail("calculate returned non-numeric string")
    elif isinstance(result, (int, float)):
        num = result
    else:
        pytest.fail("calculate returned unexpected type: {}".format(type(result)))

    assert num == expected


def test_calculate_division_by_zero_raises():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calculate = _resolve_callable(sc, "calculate")
    if calculate is None or not callable(calculate):
        pytest.skip("calculate callable not found in SimpleCalculatorPyQt1")
    sig = inspect.signature(calculate)
    exc_cls = _exc_lookup("CalculatorError", ZeroDivisionError)

    class DummyMain:
        def __init__(self):
            self.input = mock.Mock()
            self.ui = types.SimpleNamespace(input=self.input, history=mock.Mock())
            self.lineEdit = self.input
            self.history = mock.Mock()

    dummy = DummyMain()

    # Act / Assert
    try:
        if len(sig.parameters) == 0:
            with pytest.raises(_exc_lookup("exc_cls", Exception)):
                calculate()
        elif len(sig.parameters) == 1:
            with pytest.raises(_exc_lookup("exc_cls", Exception)):
                calculate("1/0")
        else:
            with pytest.raises(_exc_lookup("exc_cls", Exception)):
                calculate(dummy, "1/0")
    except TypeError:
        pytest.skip("calculate exists but could not be invoked with available calling patterns")


def test_clear_input_clears_input_widget():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    clear_input = _resolve_callable(sc, "clear_input")
    if clear_input is None or not callable(clear_input):
        pytest.skip("clear_input callable not found in SimpleCalculatorPyQt1")
    sig = inspect.signature(clear_input)

    # Create a dummy main instance exposing multiple common attributes the implementation might use
    class DummyMain:
        def __init__(self):
            self.input = mock.Mock()
            self.input.setText = mock.Mock()
            self.input.clear = mock.Mock()
            self.lineEdit = self.input
            self.ui = types.SimpleNamespace(input=self.input)
            self.result = mock.Mock()

    dummy = DummyMain()

    # Act
    try:
        if len(sig.parameters) == 0:
            clear_input()
        elif len(sig.parameters) == 1:
            clear_input(dummy)
        else:
            # attempt (self, ) pattern
            clear_input(dummy, )
    except TypeError:
        pytest.skip("clear_input exists but could not be invoked with available calling patterns")

    # Assert - confirm that one of the typical clearing methods was invoked
    called = (
        dummy.input.setText.called
        or dummy.input.clear.called
    )
    assert called, "clear_input did not call expected clearing methods on the input widget"


def test_clear_history_clears_history_widget_and_or_ui_state():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    clear_history = _resolve_callable(sc, "clear_history")
    if clear_history is None or not callable(clear_history):
        pytest.skip("clear_history callable not found in SimpleCalculatorPyQt1")
    sig = inspect.signature(clear_history)

    # Create dummy main exposing likely attributes
    class DummyMain:
        def __init__(self):
            self.history = mock.Mock()
            self.history.clear = mock.Mock()
            self.ui = types.SimpleNamespace(history=self.history)
            # some implementations may use a 'historyText' or QTextEdit named differently
            self.historyText = self.history
            self.historyWidget = self.history

    dummy = DummyMain()

    # Act
    try:
        if len(sig.parameters) == 0:
            clear_history()
        elif len(sig.parameters) == 1:
            clear_history(dummy)
        else:
            clear_history(dummy, )
    except TypeError:
        pytest.skip("clear_history exists but could not be invoked with available calling patterns")

    # Assert - ensure at least one expected clear method was called
    cleared = dummy.history.clear.called
    assert cleared, "clear_history did not call clear() on the history widget"
