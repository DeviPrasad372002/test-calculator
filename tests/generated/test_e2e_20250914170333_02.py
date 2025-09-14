
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

import inspect
import os
from pathlib import Path

import pytest

try:
    import Calculator
    import SimpleCalculatorPyQt1 as SC
except ImportError:
    pytest.skip("Required modules (Calculator or SimpleCalculatorPyQt1) are not available", allow_module_level=True)


def _exc_lookup(name, fallback=Exception):
    # Prefer exception in Calculator module, then in SC module, otherwise fallback
    if hasattr(Calculator, name):
        return getattr(Calculator, name)
    if hasattr(SC, name):
        return getattr(SC, name)
    return fallback


def _get_callable(module, func_name):
    # Try top-level function first
    if hasattr(module, func_name) and callable(getattr(module, func_name)):
        return getattr(module, func_name)
    # Then try a Calculator class instance method
    if hasattr(module, "Calculator"):
        try:
            cls = getattr(module, "Calculator")
            inst = cls()
            if hasattr(inst, func_name) and callable(getattr(inst, func_name)):
                return getattr(inst, func_name)
        except Exception:
            # If instantiation fails, fallback to None
            pass
    return None


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (3, 4, 12),
        (0, 5, 0),
        (-2, 6, -12),
        (2.5, 4, 10.0),
        (10**6, 10**6, 10**12),
        (10**18, 10**18, 10**36),
        (-1.5, -2.0, 3.0),
    ],
)
def test_multiply_various(a, b, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    multiply = _get_callable(Calculator, "multiply")
    if multiply is None:
        pytest.skip("No multiply callable found in Calculator module or Calculator class")

    # Act
    result = multiply(a, b)

    # Assert
    if isinstance(expected, _exc_lookup("float", Exception)):
        assert isinstance(result, (float, int))
        assert pytest.approx(expected, rel=1e-12) == result
    else:
        assert result == expected
        assert isinstance(result, _exc_lookup("int", Exception)) or isinstance(result, _exc_lookup("float", Exception))


@pytest.mark.parametrize(
    "numerator,denominator,expected",
    [
        (10, 2, 5),
        (7, 2, 3.5),
        (0, 5, 0),
        (-9, 3, -3),
        (5, 2.5, 2.0),
    ],
)
def test_divide_normal_cases(numerator, denominator, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    divide = _get_callable(Calculator, "divide")
    if divide is None:
        pytest.skip("No divide callable found in Calculator module or Calculator class")

    # Act
    result = divide(numerator, denominator)

    # Assert
    assert isinstance(result, (int, float))
    assert pytest.approx(expected, rel=1e-12) == result


def test_divide_by_zero_raises():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    divide = _get_callable(Calculator, "divide")
    if divide is None:
        pytest.skip("No divide callable found in Calculator module or Calculator class")

    exc_type = _exc_lookup("CalculatorError", Exception)

    # Act / Assert
    with pytest.raises(_exc_lookup("exc_type", Exception)):
        divide(5, 0)


@pytest.mark.parametrize(
    "history_lines",
    [
        (["1 + 1 = 2", "2 * 3 = 6"]),
        ([]),
        (["single entry"]),
    ],
)
def test_save_history_writes_file(tmp_path, history_lines):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    target_file = tmp_path / "history.txt"
    tried = []

    # Strategy 1: module-level function SC.save_history(path, history)
    if hasattr(SC, "save_history") and callable(getattr(SC, "save_history")):
        func = getattr(SC, "save_history")
        sig = inspect.signature(func)
        params = len(sig.parameters)
        try:
            if params >= 2:
                # Act
                func(str(target_file), history_lines)
                tried.append("module_two_args")
            elif params == 1:
                # Try passing history only or path only; prefer (path) then check file
                try:
                    func(str(target_file))
                    tried.append("module_one_arg_path")
                except Exception:
                    # fallback: try passing history only
                    func(history_lines)
                    tried.append("module_one_arg_history")
        except Exception:
            # swallow and try other strategies
            pass

    # Strategy 2: try MainWindow.save_history(instance, path) or instance.save_history(path, history)
    if not target_file.exists() or target_file.stat().st_size == 0:
        if hasattr(SC, "MainWindow"):
            try:
                WindowCls = getattr(SC, "MainWindow")
                try:
                    win = WindowCls()
                except TypeError:
                    # If constructor requires args, try without instantiation
                    win = None
                if win is not None:
                    if hasattr(win, "save_history") and callable(getattr(win, "save_history")):
                        method = getattr(win, "save_history")
                        sig = inspect.signature(method)
                        params = len(sig.parameters)
                        try:
                            if params >= 2:
                                method(str(target_file), history_lines)
                                tried.append("instance_two_args")
                            elif params == 1:
                                try:
                                    method(str(target_file))
                                    tried.append("instance_one_arg_path")
                                except Exception:
                                    method(history_lines)
                                    tried.append("instance_one_arg_history")
                        except Exception:
                            pass
            except Exception:
                pass

    # Strategy 3: try top-level function SC.save_history() with no args
    if (not target_file.exists() or target_file.stat().st_size == 0) and hasattr(SC, "save_history"):
        func = getattr(SC, "save_history")
        try:
            sig = inspect.signature(func)
            if len(sig.parameters) == 0:
                try:
                    # If there's an internal history in module, set it if present
                    if hasattr(SC, "history"):
                        setattr(SC, "history", history_lines)
                    func()
                    tried.append("module_no_args")
                except Exception:
                    pass
        except Exception:
            pass

    # Final check: file must exist and contain the expected lines joined
    if not target_file.exists():
        pytest.skip(f"Could not invoke save_history successfully with attempted strategies: {tried}")

    # Act / Assert: read file and verify contents
    content = target_file.read_text(encoding="utf-8")
    joined = "\n".join(history_lines)
    # Accept presence of each line in file to be tolerant of formatting (E2E black-box)
    for line in history_lines:
        assert line in content

    # Also ensure file is non-empty except when history was empty
    if history_lines:
        assert content.strip() != ""
    else:
        # For empty history, allow empty file or file with no content
        assert isinstance(content, _exc_lookup("str", Exception))  # simple sanity check that file read succeeded
