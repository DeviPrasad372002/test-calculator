import pytest, sys, os, warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if os.getenv("TESTGEN_FIX_JINJA2","1") in ("1","true","yes"):
    def _fix_jinja2_compatibility():
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
    _fix_jinja2_compatibility()

if os.getenv("TESTGEN_FIX_COLLECTIONS","1") in ("1","true","yes"):
    def _fix_collections_compatibility():
        try:
            import collections
            import collections.abc as abc
            for name in ['Mapping','MutableMapping','Sequence','Iterable','Container',
                         'MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection']:
                if not hasattr(collections, name) and hasattr(abc, name):
                    setattr(collections, name, getattr(abc, name))
        except ImportError:
            pass
    _fix_collections_compatibility()

if os.getenv("TESTGEN_FIX_FLASK","0") in ("1","true","yes"):
    def _fix_flask_compatibility():
        try:
            import flask
            if not hasattr(flask, 'escape'):
                try:
                    from markupsafe import escape
                    flask.escape = escape
                except Exception:
                    pass
        except ImportError:
            pass
    _fix_flask_compatibility()

def _fix_marshmallow_compatibility():
    try:
        import marshmallow as _mm
        if not hasattr(_mm, "__version__"):
            _mm.__version__ = "4"
    except Exception:
        pass

_fix_marshmallow_compatibility()

os.environ.setdefault('WTF_CSRF_ENABLED', 'False')
