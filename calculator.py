"""
Safe expression evaluator (no `eval` on raw input) plus percentage
helpers and a small unit-conversion table covering common
length/weight/temperature/data conversions.
"""
import ast
import operator

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.FloorDiv: operator.floordiv,
}


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Invalid constant in expression")
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Unsupported expression")


def safe_eval(expression: str) -> float:
    expression = expression.replace("^", "**").replace("x", "*").replace("×", "*").replace("÷", "/")
    try:
        tree = ast.parse(expression, mode="eval")
        return _eval_node(tree.body)
    except Exception as e:
        raise ValueError(f"Couldn't evaluate expression: {e}")


def percent_of(value: float, percent: float) -> float:
    return value * percent / 100


def percent_change(old: float, new: float) -> float:
    if old == 0:
        raise ValueError("Cannot compute percent change from 0")
    return (new - old) / old * 100


# unit -> (category, factor to base unit)
_LENGTH = {"mm": 0.001, "cm": 0.01, "m": 1, "km": 1000, "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344}
_WEIGHT = {"mg": 0.001, "g": 1, "kg": 1000, "oz": 28.3495, "lb": 453.592, "ton": 1_000_000}
_DATA = {"b": 1 / 8, "kb": 1000 / 8, "mb": 1_000_000 / 8, "gb": 1_000_000_000 / 8, "byte": 1, "bytes": 1,
          "kib": 1024, "mib": 1024 ** 2, "gib": 1024 ** 3}


def convert_unit(value: float, from_unit: str, to_unit: str) -> float:
    from_unit, to_unit = from_unit.lower(), to_unit.lower()

    if from_unit in ("c", "celsius") or to_unit in ("c", "celsius") or \
       from_unit in ("f", "fahrenheit") or to_unit in ("f", "fahrenheit") or \
       from_unit in ("k", "kelvin") or to_unit in ("k", "kelvin"):
        return _convert_temperature(value, from_unit, to_unit)

    for table in (_LENGTH, _WEIGHT, _DATA):
        if from_unit in table and to_unit in table:
            base = value * table[from_unit]
            return base / table[to_unit]

    raise ValueError(f"Don't know how to convert '{from_unit}' to '{to_unit}'")


def _convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    f, t = from_unit[0], to_unit[0]
    if f == t:
        return value
    # normalize to Celsius first
    if f == "f":
        c = (value - 32) * 5 / 9
    elif f == "k":
        c = value - 273.15
    else:
        c = value

    if t == "f":
        return c * 9 / 5 + 32
    elif t == "k":
        return c + 273.15
    return c
