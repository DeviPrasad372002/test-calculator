import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

try:
    import importlib
except ModuleNotFoundError:
    try:
        import importlib
    except ModuleNotFoundError:
        import importlib.util, sys, os
        _tr=os.environ.get('TARGET_ROOT') or 'target'
        _p1=os.path.join(_tr, 'importlib.py'); _p2=os.path.join(_tr, 'importlib.py')
        _pp=[_p for _p in (_p1,_p2) if os.path.isfile(_p)]
        if _pp:
            _spec=importlib.util.spec_from_file_location('importlib', _pp[0])
            _m=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
            sys.modules.setdefault('importlib', _m)
        else:
            raise

try:
    import inspect
except ModuleNotFoundError:
    try:
        import inspect
    except ModuleNotFoundError:
        import importlib.util, sys, os
        _tr=os.environ.get('TARGET_ROOT') or 'target'
        _p1=os.path.join(_tr, 'inspect.py'); _p2=os.path.join(_tr, 'inspect.py')
        _pp=[_p for _p in (_p1,_p2) if os.path.isfile(_p)]
        if _pp:
            _spec=importlib.util.spec_from_file_location('inspect', _pp[0])
            _m=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
            sys.modules.setdefault('inspect', _m)
        else:
            raise

try:
    import numbers
except ModuleNotFoundError:
    try:
        import numbers
    except ModuleNotFoundError:
        import importlib.util, sys, os
        _tr=os.environ.get('TARGET_ROOT') or 'target'
        _p1=os.path.join(_tr, 'numbers.py'); _p2=os.path.join(_tr, 'numbers.py')
        _pp=[_p for _p in (_p1,_p2) if os.path.isfile(_p)]
        if _pp:
            _spec=importlib.util.spec_from_file_location('numbers', _pp[0])
            _m=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
            sys.modules.setdefault('numbers', _m)
        else:
            raise

try:
    import pytest
except ModuleNotFoundError:
    try:
        import pytest
    except ModuleNotFoundError:
        import importlib.util, sys, os
        _tr=os.environ.get('TARGET_ROOT') or 'target'
        _p1=os.path.join(_tr, 'pytest.py'); _p2=os.path.join(_tr, 'pytest.py')
        _pp=[_p for _p in (_p1,_p2) if os.path.isfile(_p)]
        if _pp:
            _spec=importlib.util.spec_from_file_location('pytest', _pp[0])
            _m=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
            sys.modules.setdefault('pytest', _m)
        else:
            raise

_calc_mod = None
for _name in ("target.Calculator", "Calculator"):
    try:
        _calc_mod = importlib.import_module(_name)
        break
    except ImportError:
        _calc_mod = None

if _calc_mod is None:
    pytest.skip("target.Calculator module not importable from 'target.Calculator' or 'Calculator'", allow_module_level=True)

Calculator = getattr(_calc_mod, "Calculator", None)
CalculatorError = getattr(_calc_mod, "CalculatorError", None)

# If a specific CalculatorError is not provided by the module, fall back to ValueError for tests that expect an error class.
ErrorClass = CalculatorError if CalculatorError is not None else ValueError

def _has_method(obj, name):
    return hasattr(obj, name) and callable(getattr(obj, name))

def _get_state_value(instance):
    # Common attribute names for internal state
    for attr in ("value", "current", "total", "result", "memory"):
        if hasattr(instance, attr):
            val = getattr(instance, attr)
            if isinstance(val, numbers.Number):
                return val
    return None

def _call_add(instance_or_module, *args):
    
    if Calculator is not None and isinstance(instance_or_module, Calculator):
        func = getattr(instance_or_module, "add", None)
    else:
        func = getattr(instance_or_module, "add", None)
    if func is None or not callable(func):
        raise AttributeError("add function/method not found")
    return func(*args)

def _call_subtract(instance_or_module, *args):
    if Calculator is not None and isinstance(instance_or_module, Calculator):
        func = getattr(instance_or_module, "subtract", None)
    else:
        func = getattr(instance_or_module, "subtract", None)
    if func is None or not callable(func):
        raise AttributeError("subtract function/method not found")
    return func(*args)

def _instantiate_with_optional_initial(cls, initial):
    # Determine if __init__ accepts an initial value (besides self)
    sig = inspect.signature(cls.__init__)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    if len(params) == 0:
        # No initial allowed
        return cls()
    # If there is at least one non-self parameter, try providing one positional initial value.
    return cls(initial)

def _extract_numeric(result, instance_if_any):
    # If the operation returned a numeric value, use it.
    if isinstance(result, numbers.Number):
        return result
    # Otherwise, attempt to find state value on instance
    if instance_if_any is not None:
        val = _get_state_value(instance_if_any)
        if isinstance(val, numbers.Number):
            return val
    # Could not extract numeric
    raise AssertionError("Operation did not return numeric and no numeric state found")

def test___init_creates_instance_and_has_operations():
    
    # Arrange / Act
    assert Calculator is not None, "Calculator class is required for this test"
    inst = Calculator()  
    # Assert
    assert isinstance(inst, Calculator)
    assert _has_method(inst, "add"), "Calculator must have an add method"
    assert _has_method(inst, "subtract"), "Calculator must have a subtract method"

@pytest.mark.parametrize("initial,operand,expected_after_add", [
    (0, 5, 5),
    (10, 3, 13),
    (-2, 7, 5),
    (1.5, 2.5, 4.0),
])
def test_add_updates_state_or_returns_sum_with_instance(initial, operand, expected_after_add):
    
    # Arrange
    assert Calculator is not None, "Calculator class is required"
    inst = _instantiate_with_optional_initial(Calculator, initial)
    # Act
    returned = _call_add(inst, operand)
    # Assert: either method returns numeric sum or updates internal state to expected_after_add
    result_numeric = None
    if isinstance(returned, numbers.Number):
        result_numeric = returned
    else:
        result_numeric = _get_state_value(inst)
    assert isinstance(result_numeric, numbers.Number)
    # Allow small float tolerance for float inputs
    if isinstance(expected_after_add, float):
        assert abs(result_numeric - expected_after_add) < 1e-9
    else:
        assert result_numeric == expected_after_add

@pytest.mark.parametrize("initial,operand,expected_after_subtract", [
    (0, 5, -5),
    (10, 3, 7),
    (-2, 7, -9),
    (5.5, 2.0, 3.5),
])
def test_subtract_updates_state_or_returns_difference_with_instance(initial, operand, expected_after_subtract):
    
    # Arrange
    assert Calculator is not None, "Calculator class is required"
    inst = _instantiate_with_optional_initial(Calculator, initial)
    # Act
    returned = _call_subtract(inst, operand)
    # Assert
    result_numeric = None
    if isinstance(returned, numbers.Number):
        result_numeric = returned
    else:
        result_numeric = _get_state_value(inst)
    assert isinstance(result_numeric, numbers.Number)
    if isinstance(expected_after_subtract, float):
        assert abs(result_numeric - expected_after_subtract) < 1e-9
    else:
        assert result_numeric == expected_after_subtract

@pytest.mark.parametrize("bad_input", [
    "not a number",
    None,
    object(),
])
def test_add_raises_on_invalid_input(bad_input):
    
    # Arrange
    assert Calculator is not None, "Calculator class is required"
    inst = _instantiate_with_optional_initial(Calculator, 0)
    
    with pytest.raises(ErrorClass):
        _call_add(inst, bad_input)

@pytest.mark.parametrize("bad_input", [
    "bad",
    None,
    [],
])
def test_subtract_raises_on_invalid_input(bad_input):
    
    # Arrange
    assert Calculator is not None, "Calculator class is required"
    inst = _instantiate_with_optional_initial(Calculator, 0)
    # Act / Assert
    with pytest.raises(ErrorClass):
        _call_subtract(inst, bad_input)

def test_add_and_subtract_as_module_level_functions_if_present():
    
    # This test verifies behavior if module exposes top-level add/subtract functions (stateless)
    mod = _calc_mod
    if not (hasattr(mod, "add") and hasattr(mod, "subtract")):
        pytest.skip("Module-level add/subtract not present; skipping stateless function tests")
    add_fn = getattr(mod, "add")
    subtract_fn = getattr(mod, "subtract")
    # Inspect signatures
    add_sig = inspect.signature(add_fn)
    subtract_sig = inspect.signature(subtract_fn)
    # Expect two-argument signatures for stateless functions: add(a, b) and subtract(a, b)
    assert len([p for p in add_sig.parameters.values()]) == 2
    assert len([p for p in subtract_sig.parameters.values()]) == 2
    # Concrete checks
    assert add_fn(2, 3) == 5
    assert add_fn(2.5, 1.5) == 4.0
    assert subtract_fn(10, 4) == 6
    assert abs(subtract_fn(5.5, 2.0) - 3.5) < 1e-9
