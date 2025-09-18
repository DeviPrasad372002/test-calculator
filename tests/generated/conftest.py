import pytest, sys, os, warnings, types as _types, builtins, importlib
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

_tr = os.environ.get("TARGET_ROOT", "target")
if _tr and os.path.isdir(_tr):
    _parent = os.path.abspath(os.path.join(_tr, os.pardir))
    for p in (_parent, _tr):
        if p not in sys.path:
            sys.path.insert(0, p)
    if "target" not in sys.modules:
        _pkg = _types.ModuleType("target")
        _pkg.__path__ = [_tr]
        sys.modules["target"] = _pkg

# Case-insensitive import fallback for local modules
_real_import = builtins.__import__
def _smart_import(name, *args, **kwargs):
    try:
        return _real_import(name, *args, **kwargs)
    except ModuleNotFoundError as e:
        base = os.environ.get("TARGET_ROOT") or "target"
        low = name.lower()
        if low != name:
            try:
                return _real_import(low, *args, **kwargs)
            except ModuleNotFoundError:
                pass
        # try file-based resolution inside target root
        cand = os.path.join(base, f"{name}.py")
        cand_low = os.path.join(base, f"{low}.py")
        if os.path.isfile(cand):
            spec = importlib.util.spec_from_file_location(name, cand)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
                sys.modules[name] = mod
                return mod
        if os.path.isfile(cand_low):
            spec = importlib.util.spec_from_file_location(low, cand_low)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
                sys.modules[low] = mod
                return mod
        raise e
builtins.__import__ = _smart_import

# Compatibility fixes
def _fix():
    try:
        import jinja2
        if not hasattr(jinja2,'Markup'):
            from markupsafe import Markup, escape
            jinja2.Markup = Markup
            if not hasattr(jinja2,'escape'):
                jinja2.escape = escape
    except Exception: pass
    try:
        import collections, collections.abc as abc
        for n in ['Mapping','MutableMapping','Sequence','Iterable','Container','MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection']:
            if not hasattr(collections,n) and hasattr(abc,n):
                setattr(collections,n,getattr(abc,n))
    except Exception: pass
_fix()

@pytest.fixture
def expected_status(): return 404

@pytest.fixture
def expected_status_code(expected_status): return expected_status

@pytest.fixture
def CalcError(): return ZeroDivisionError

os.environ.setdefault('WTF_CSRF_ENABLED', 'False')
