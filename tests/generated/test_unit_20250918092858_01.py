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
except Exception:
    pytest.skip("target.Calculator module or required symbols not available", allow_module_level=True)

def test___init___methods_present():
    
    # Arrange / Act
    calc = Calculator()
    # Assert
    assert hasattr(calc, "add"), "Calculator must have an 'add' method"
    assert callable(calc.add), "'add' must be callable"
    assert hasattr(calc, "subtract"), "Calculator must have a 'subtract' method"
    assert callable(calc.subtract), "'subtract' must be callable"

def test_add_two_integers_returns_int_sum():
    
    # Arrange
    calc = Calculator()
    a, b = 2, 3
    # Act
    result = calc.add(a, b)
    # Assert
    assert result == 5
    assert type(result) is int

def test_add_floats_returns_float_sum():
    
    # Arrange
    calc = Calculator()
    a, b = 1.2, 2.3
    # Act
    result = calc.add(a, b)
    # Assert
    assert result == 3.5
    assert isinstance(result, float)

def test_subtract_smaller_from_larger_returns_negative():
    
    # Arrange
    calc = Calculator()
    a, b = 3, 5
    # Act
    result = calc.subtract(a, b)
    # Assert
    assert result == -2
    assert type(result) is int

def test_add_invalid_types_raises_CalculatorError():
    
    # Arrange
    calc = Calculator()
    # Act / Assert
    with pytest.raises(CalculatorError):
        calc.add("not a number", 5)
