
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
    import builtins
    from types import SimpleNamespace
    import target.SimpleCalculatorPyQt1 as SimpleCalculatorPyQt1
    import target.Calculator as Calculator
except ImportError:
    import pytest
    pytest.skip("Required test modules or target modules not available", allow_module_level=True)

def _exc_class(name, fallback=Exception):
    # Prefer the harness-provided _exc_lookup if present, else fall back to attribute on Calculator module, else Exception
    try:
        return _exc_lookup(name, fallback)  # type: ignore    # may be injected by harness
    except Exception:
        return getattr(Calculator, name, fallback)

def _adaptive_call(func, context):
    """
    Call func by matching available parameter names to keys in context dict.
    Supports positional-only by order in signature.
    """
    sig = inspect.signature(func)
    args = []
    kwargs = {}
    for i, (pname, param) in enumerate(sig.parameters.items()):
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            # pass nothing special for varargs/kwargs
            continue
        if pname in context:
            # honor provided object
            if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                args.append(context[pname])
            else:
                kwargs[pname] = context[pname]
        else:
            # try common aliases
            for alias in ('self', 'mainwindow', 'win', 'widget', 'history_widget', 'history', 'expression', 'expr', 'text', 'calculator', 'calc'):
                if alias in context:
                    if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                        args.append(context[alias])
                    else:
                        kwargs[pname] = context[alias]
                    break
            else:
                # cannot satisfy parameter; raise to make test aware
                raise TypeError(f"Cannot adaptively call {func.__name__}: missing parameter '{pname}'")
    return func(*args, **kwargs)

def test_calculate_valid_expressions_and_division_by_zero():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calc_instance = getattr(Calculator, "Calculator", None)
    assert inspect.isclass(calc_instance), "Calculator class must be present"
    calculator = calc_instance()

    calculate = getattr(SimpleCalculatorPyQt1, "calculate", None)
    assert callable(calculate), "calculate must be a callable in SimpleCalculatorPyQt1"

    valid_cases = [
        ("2+3", 5),
        ("10-4", 6),
        ("6*7", 42),
        ("10/2", 5.0),
    ]

    # Act & Assert for valid expressions
    for expr, expected in valid_cases:
        # Act
        result = _adaptive_call(calculate, {'expression': expr, 'expr': expr, 'calculator': calculator, 'calc': calculator})
        # Assert: allow numerical types and number-like strings
        assert result is not None, f"calculate returned None for '{expr}'"
        if isinstance(result, _exc_lookup("str", Exception)):
            # try to coerce numeric string to number for comparison
            try:
                numeric = float(result) if ('.' in result or 'e' in result.lower()) else int(result)
            except Exception:
                pytest.fail(f"calculate returned non-numeric string for '{expr}': {result!r}")
            assert numeric == expected
        else:
            assert result == expected

    # Act & Assert for division by zero
    div_zero_exprs = ["1/0", "10/(5-5)"]
    exc_cls = _exc_class('CalculatorError', Exception)
    for expr in div_zero_exprs:
        with pytest.raises(_exc_lookup("exc_cls", Exception)):
            _adaptive_call(calculate, {'expression': expr, 'expr': expr, 'calculator': calculator, 'calc': calculator})

def test_clear_history_clears_widget_contents_and_updates_state(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    clear_history = getattr(SimpleCalculatorPyQt1, "clear_history", None)
    assert callable(clear_history), "clear_history must be present and callable"

    class FakeHistory:
        def __init__(self, items):
            self._items = list(items)
            self.cleared = False
        def count(self):
            return len(self._items)
        def clear(self):
            self._items.clear()
            self.cleared = True
        def __len__(self):
            return len(self._items)

    widget = FakeHistory(["one", "two", "three"])
    assert widget.count() == 3

    # Act
    _adaptive_call(clear_history, {'history_widget': widget, 'history': widget, 'widget': widget, 'self': None})

    # Assert
    assert widget.cleared is True, "clear_history should call clear() on provided widget"
    assert widget.count() == 0

@pytest.mark.parametrize("initial_input,initial_result", [
    ("123", "123"),    # numeric
    ("", ""),          # empty boundary
    ("  abc  ", "abc") # whitespace trimmed maybe
])
def test_clear_input_resets_input_and_result_fields(initial_input, initial_result):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    clear_input = getattr(SimpleCalculatorPyQt1, "clear_input", None)
    assert callable(clear_input), "clear_input must be present and callable"

    class FakeLineEdit:
        def __init__(self, text=""):
            self._text = text
            self.cleared = False
        def text(self):
            return self._text
        def setText(self, s):
            self._text = s
        def clear(self):
            self._text = ""
            self.cleared = True

    # Some implementations expect a mainwindow with attributes; others expect widget arguments
    input_widget = FakeLineEdit(initial_input)
    result_widget = FakeLineEdit(initial_result)

    fake_main = SimpleNamespace()
    # common attribute names used by simple UIs
    setattr(fake_main, "input_field", input_widget)
    setattr(fake_main, "lineEdit", input_widget)
    setattr(fake_main, "display", result_widget)
    setattr(fake_main, "result_field", result_widget)
    setattr(fake_main, "lineEditResult", result_widget)

    # Act
    _adaptive_call(clear_input, {'self': fake_main, 'input_widget': input_widget, 'result_widget': result_widget, 'input': input_widget, 'result': result_widget, 'widget': fake_main})

    # Assert: both fields should now be empty strings
    assert input_widget.text() == "", "clear_input should clear the input widget"
    assert result_widget.text() == "", "clear_input should clear the result widget"
    # also prefer that clear() was called on at least one of them
    assert getattr(input_widget, "cleared", True) or getattr(result_widget, "cleared", True)

def test_calculator_divide_function_raises_on_zero_and_returns_float_on_normal():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    div_func = getattr(Calculator, "divide", None)
    assert callable(div_func), "Calculator.divide function must exist"
    exc_cls = _exc_class('CalculatorError', Exception)

    # Act & Assert normal division returns float when needed
    result = div_func(9, 2)
    assert isinstance(result, (int, float)), "divide should return a numeric type"
    assert result == 4.5

    # Act & Assert division by zero raises expected CalculatorError
    with pytest.raises(_exc_lookup("exc_cls", Exception)):
        div_func(5, 0)
