import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

try:
    import pytest
    from target import Calculator as calcmod
except Exception:
    import pytest
    pytest.skip("target.Calculator module not importable", allow_module_level=True)

from unittest.mock import Mock

# Helper to retrieve required attributes or skip if missing
def _get_or_skip(attr_name):
    if not hasattr(calcmod, attr_name):
        pytest.skip(f"target.Calculator missing required attribute '{attr_name}'", allow_module_level=False)
    return getattr(calcmod, attr_name)

@pytest.mark.parametrize(
    "op_name,a,b,expected_type,expected_value",
    [
        ("add", 1, 2, int, 3),
        ("subtract", 5, 2, int, 3),
        ("multiply", 3, 4, int, 12),
        ("divide", 8, 4, float, 2.0),
    ],
)
def test_function_and_method_consistency_basic_ops(op_name, a, b, expected_type, expected_value, monkeypatch):
    
    # Arrange
    Calculator = _get_or_skip("Calculator")
    func = _get_or_skip(op_name)
    # Mock external boundaries if the module imported common side-effect modules
    if hasattr(calcmod, "os") and hasattr(calcmod.os, "system"):
        monkeypatch.setattr(calcmod.os, "system", lambda *args, **kwargs: 0)
    if hasattr(calcmod, "random") and hasattr(calcmod.random, "random"):
        monkeypatch.setattr(calcmod.random, "random", lambda: 0.0)
    instance = Calculator()

    # Act
    result_func = func(a, b)
    
    method = getattr(instance, op_name, None)
    if method is None:
        pytest.skip(f"Calculator instance missing method '{op_name}'")
    result_method = method(a, b)

    # Assert
    assert type(result_func) is expected_type, "standalone function returned unexpected type"
    assert type(result_method) is expected_type, "instance method returned unexpected type"
    assert result_func == expected_value
    assert result_method == expected_value
    assert result_func == result_method

def test_divide_by_zero_raises_calculator_error(monkeypatch):
    
    # Arrange
    Calculator = _get_or_skip("Calculator")
    divide_fn = _get_or_skip("divide")
    CalcError = _get_or_skip("CalculatorError")
    if hasattr(calcmod, "os") and hasattr(calcmod.os, "system"):
        monkeypatch.setattr(calcmod.os, "system", lambda *args, **kwargs: 0)
    instance = Calculator()

    # Act / Assert for standalone function
    with pytest.raises(CalcError):
        divide_fn(10, 0)

    # Act / Assert for instance method
    method = getattr(instance, "divide", None)
    if method is None:
        pytest.skip("Calculator instance missing method 'divide'")
    with pytest.raises(CalcError):
        method(10, 0)

@pytest.mark.parametrize("a,b", [
    ("a", 1),
    (None, 2),
    (1, "b"),
    ([], {}),
])
def test_non_numeric_inputs_raise_calculator_error(a, b, monkeypatch):
    
    # Arrange
    CalcError = _get_or_skip("CalculatorError")
    Calculator = _get_or_skip("Calculator")
    add_fn = _get_or_skip("add")
    if hasattr(calcmod, "random") and hasattr(calcmod.random, "random"):
        monkeypatch.setattr(calcmod.random, "random", lambda: 0.0)
    if hasattr(calcmod, "os") and hasattr(calcmod.os, "system"):
        monkeypatch.setattr(calcmod.os, "system", lambda *args, **kwargs: 0)
    instance = Calculator()

    # Act / Assert for standalone function
    with pytest.raises(CalcError):
        add_fn(a, b)

    # Act / Assert for instance method
    method = getattr(instance, "add", None)
    if method is None:
        pytest.skip("Calculator instance missing method 'add'")
    with pytest.raises(CalcError):
        method(a, b)
