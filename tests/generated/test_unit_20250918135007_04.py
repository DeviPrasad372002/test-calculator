import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import pytest

try:
    from target.Calculator import Calculator, CalculatorError
    from target.SimpleCalculatorPyQt1 import MainWindow
except Exception:
    pytest.skip("Required target modules (Calculator or SimpleCalculatorPyQt1/PyQt5) not available", allow_module_level=True)

@pytest.mark.parametrize(
    "a,b,method_name,expected",
    [
        (3, 5, "add", 8),
        (10, 4, "subtract", 6),
        (6, 7, "multiply", 42),
        (20, 5, "divide", 4),
    ],
)
def test_Calculator_arithmetic_operations_parametrized(a, b, method_name, expected):
    
    # Arrange
    calc = Calculator()

    # Act
    method = getattr(calc, method_name)
    result = method(a, b)

    # Assert
    assert isinstance(result, (int, float)), "result should be numeric"
    assert result == expected

def test_Calculator_divide_by_zero_raises_CalculatorError():
    
    # Arrange
    calc = Calculator()

    # Act / Assert
    with pytest.raises(CalculatorError):
        calc.divide(1, 0)

def test_Calculator_instance_has_public_methods_and_type():
    
    # Arrange / Act
    calc = Calculator()

    # Assert
    assert isinstance(calc, Calculator)
    for name in ("add", "subtract", "multiply", "divide"):
        member = getattr(calc, name, None)
        assert callable(member), f"Calculator should have callable '{name}'"

def test_MainWindow_class_exposes_expected_methods():
    
    # Arrange / Act
    cls = MainWindow

    # Assert: ensure the UI class defines the public utility methods on the class (no Qt instantiation)
    for method_name in ("clear_history", "clear_input", "calculate", "save_history"):
        member = getattr(cls, method_name, None)
        assert member is not None, f"MainWindow should define '{method_name}'"
        assert callable(member), f"MainWindow.{method_name} should be callable"
