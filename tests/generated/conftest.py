import os, importlib.util, warnings, pytest
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)

for _m in ("fastapi","flask","django","rest_framework","sqlalchemy","starlette","pydantic"):
    if _m in ("django","rest_framework"):
        # don't import django automatically — only skip module imports
        continue
    if importlib.util.find_spec(_m) is None:
        # module-level skip happens inside tests via runtime_guard too
        pass

@pytest.fixture(autouse=True)
def _seed_random(monkeypatch):
    import random
    random.seed(1337)
    return
