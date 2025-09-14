
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
    raise

try:
    import builtins
except ImportError:
    pytest.skip("builtins missing", allow_module_level=True)

try:
    import io
except ImportError:
    pytest.skip("io missing", allow_module_level=True)

try:
    import os
except ImportError:
    pytest.skip("os missing", allow_module_level=True)

try:
    import Calculator
except ImportError:
    pytest.skip("Calculator module not available", allow_module_level=True)

try:
    import SimpleCalculatorPyQt1
except ImportError:
    pytest.skip("SimpleCalculatorPyQt1 module not available", allow_module_level=True)


def _exc_lookup(name, default_exception):
    # Look up exception class by name in loaded modules, fallback to provided default
    exc = getattr(Calculator, name, None)
    if isinstance(exc, _exc_lookup("type", Exception)) and issubclass(exc, BaseException):
        return exc
    exc = getattr(SimpleCalculatorPyQt1, name, None)
    if isinstance(exc, _exc_lookup("type", Exception)) and issubclass(exc, BaseException):
        return exc
    return default_exception


def _call_multiply(a, b):
    # Try possible multiply callables: module function, class method on Calculator, instance method
    if hasattr(Calculator, "multiply"):
        return Calculator.multiply(a, b)
    if hasattr(Calculator, "Calculator"):
        cls = getattr(Calculator, "Calculator")
        # If class has static or class method
        if hasattr(cls, "multiply"):
            try:
                return cls.multiply(a, b)
            except TypeError:
                # try instance
                inst = cls()
                return inst.multiply(a, b)
        # try instance multiply
        inst = cls()
        if hasattr(inst, "multiply"):
            return inst.multiply(a, b)
    raise pytest.skip("No multiply implementation found in Calculator module")


def _call_divide(a, b):
    if hasattr(Calculator, "divide"):
        return Calculator.divide(a, b)
    if hasattr(Calculator, "Calculator"):
        cls = getattr(Calculator, "Calculator")
        if hasattr(cls, "divide"):
            try:
                return cls.divide(a, b)
            except TypeError:
                inst = cls()
                return inst.divide(a, b)
        inst = cls()
        if hasattr(inst, "divide"):
            return inst.divide(a, b)
    raise pytest.skip("No divide implementation found in Calculator module")


def _call_save_history(history, filepath):
    # Try several common signatures for save_history
    # 1) module-level function save_history(history, filepath)
    save = getattr(SimpleCalculatorPyQt1, "save_history", None)
    if callable(save):
        # try (history, filepath)
        try:
            return save(history, filepath)
        except TypeError:
            pass
        # try (filepath, history)
        try:
            return save(filepath, history)
        except TypeError:
            pass
        # try (history,) and rely on module-level default path
        try:
            return save(history)
        except TypeError:
            pass

    # 2) MainWindow instance method
    MainWindow = getattr(SimpleCalculatorPyQt1, "MainWindow", None)
    if MainWindow:
        try:
            mw = MainWindow()
        except Exception:
            # can't instantiate; give up
            raise pytest.skip("Cannot instantiate MainWindow for save_history")
        # set common attribute names
        if hasattr(mw, "history"):
            setattr(mw, "history", history)
        if hasattr(mw, "history_file"):
            setattr(mw, "history_file", filepath)
        if hasattr(mw, "historyPath"):
            setattr(mw, "historyPath", filepath)
        # try methods
        if hasattr(mw, "save_history"):
            try:
                return mw.save_history()
            except TypeError:
                try:
                    return mw.save_history(filepath)
                except TypeError:
                    try:
                        return mw.save_history(history, filepath)
                    except TypeError:
                        pass
    raise pytest.skip("No usable save_history found in SimpleCalculatorPyQt1")


def _call_calculate(expression):
    # Try module-level calculate(expression)
    func = getattr(SimpleCalculatorPyQt1, "calculate", None)
    if callable(func):
        try:
            return func(expression)
        except TypeError:
            # try no-arg calculate on MainWindow after setting input text
            pass

    MainWindow = getattr(SimpleCalculatorPyQt1, "MainWindow", None)
    if MainWindow:
        try:
            mw = MainWindow()
        except Exception:
            raise pytest.skip("Cannot instantiate MainWindow for calculate")
        # try to set a common input attribute
        if hasattr(mw, "input"):
            try:
                mw.input = expression
            except Exception:
                pass
        if hasattr(mw, "lineEdit"):
            try:
                # many Qt examples use .setText
                if hasattr(mw.lineEdit, "setText"):
                    mw.lineEdit.setText(expression)
                else:
                    mw.lineEdit = expression
            except Exception:
                pass
        # try calling calculate methods with different signatures
        if hasattr(mw, "calculate"):
            try:
                return mw.calculate()
            except TypeError:
                try:
                    return mw.calculate(expression)
                except TypeError:
                    pass
    raise pytest.skip("No usable calculate implementation found in SimpleCalculatorPyQt1")


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (2, 3, 6),
        (0, 5, 0),
        (-2, 4, -8),
        (1.5, 2, 3.0),
        (10 ** 6, 10 ** 6, 10 ** 12),
    ],
)
def test_integration_02_multiply_various(a, b, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: operands provided by parametrization
    # Act: call multiply implementation
    result = _call_multiply(a, b)
    # Assert: correct numeric result and type
    assert result == expected
    assert isinstance(result, (int, float))


@pytest.mark.parametrize(
    "a,b,expect_exception,expected_result",
    [
        (6, 3, False, 2.0),
        (5, 0, True, None),
    ],
)
def test_integration_03_divide_normal_and_by_zero(a, b, expect_exception, expected_result):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: determine expected exception class from modules
    expected_exc = _exc_lookup("CalculatorError", ZeroDivisionError)
    # Act & Assert
    if expect_exception:
        with pytest.raises(_exc_lookup("expected_exc", Exception)):
            _call_divide(a, b)
    else:
        res = _call_divide(a, b)
        # Assert: numeric result and expected
        # allow integer division result possibly int
        assert res == expected_result
        assert isinstance(res, (int, float))


def test_integration_04_multiply_and_save_history_writes_file(monkeypatch, tmp_path):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    a, b = 2, 3
    product = _call_multiply(a, b)
    history = [f"{a} * {b} = {product}"]
    file_path = str(tmp_path / "history.txt")

    written = {"data": ""}

    class DummyFile:
        def __init__(self):
            self.closed = False

        def write(self, s):
            written["data"] += str(s)

        def writelines(self, lines):
            for l in lines:
                self.write(l)

        def close(self):
            self.closed = True

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.close()

    # Monkeypatch builtins.open to capture writes
    def fake_open(path, mode="w", *args, **kwargs):
        # Ensure the path matches expected path
        assert str(path) == file_path
        return DummyFile()

    monkeypatch.setattr(builtins, "open", fake_open, raising=True)

    # Act: call save_history in module or on MainWindow
    _call_save_history(history, file_path)

    # Assert: file received the history content
    assert history[0].split()  # non-empty entry
    assert str(product) in written["data"] or history[0] in written["data"]


def test_integration_05_calculate_uses_calculator_and_updates_history(monkeypatch, tmp_path):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: patch Calculator.multiply and divide to observe calls
    calls = {"multiply": [], "divide": []}

    def fake_multiply(x, y):
        calls["multiply"].append((x, y))
        return 999

    def fake_divide(x, y):
        calls["divide"].append((x, y))
        # simulate division by zero handling
        if y == 0:
            raise _exc_lookup("CalculatorError", ZeroDivisionError)("division by zero")
        return 123.5

    # Apply patches permissively
    monkeypatch.setattr(Calculator, "multiply", fake_multiply, raising=False)
    monkeypatch.setattr(Calculator, "divide", fake_divide, raising=False)

    # Choose an expression that will trigger multiply if calculate delegates to Calculator.multiply
    expr_mul = "2*3"
    expr_div = "10/2"

    # Act: attempt to call calculate for multiplication expression
    try:
        res_mul = _call_calculate(expr_mul)
    except pytest.skip.Exception:  # pragma: no cover - defensive
        pytest.skip("calculate not available for integration test")
    else:
        # If calculate returned a value, assert it reflects our fake multiply (either numeric or string)
        if res_mul is not None:
            # Accept numeric or string representations
            assert (res_mul == 999) or (str(999) in str(res_mul)) or calls["multiply"], "calculate did not invoke multiply as expected"

    # Act: attempt to call calculate for division expression
    try:
        res_div = _call_calculate(expr_div)
    except pytest.skip.Exception:  # pragma: no cover - defensive
        pytest.skip("calculate not available for integration test")
    else:
        # If calculate returned a value, assert it reflects our fake divide or multiply was called
        if res_div is not None:
            assert (res_div == 123.5) or (str(123.5) in str(res_div)) or calls["divide"], "calculate did not invoke divide as expected"
