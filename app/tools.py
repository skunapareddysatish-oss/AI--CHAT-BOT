"""Tools available to the assistant and Gemini function calling."""

import ast
import math
import operator
from datetime import datetime

from app.weather import (
    get_rain_prediction,
    get_tomorrow_weather,
    get_weather,
    get_weather_forecast,
)
from app.web_search import web_search
from app.wikipedia import wikipedia_search


def get_time() -> str:
    """Return the current server-local time."""
    return datetime.now().strftime("%I:%M %p")


def get_date() -> str:
    """Return today's date."""
    return datetime.now().strftime("%d %B %Y")


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MATH_FUNCTIONS = {
    "sqrt": math.sqrt,
    "pow": pow,
    "abs": abs,
    "round": round,
}


def _evaluate_math(node: ast.AST):
    if isinstance(node, ast.Expression):
        return _evaluate_math(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_math(node.left)
        right = _evaluate_math(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Exponent is too large")
        return _BINARY_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate_math(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        function = _MATH_FUNCTIONS.get(node.func.id)
        if function is None or node.keywords:
            raise ValueError("Function is not allowed")
        return function(*[_evaluate_math(argument) for argument in node.args])
    raise ValueError("Expression contains unsupported syntax")


def calculator(expression: str) -> str:
    """Safely evaluate a small mathematical expression."""
    if not expression or len(expression) > 200:
        return "Invalid mathematical expression."

    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate_math(tree)
        if isinstance(result, float) and not math.isfinite(result):
            raise ValueError("Result is not finite")
        return str(result)
    except (ArithmeticError, SyntaxError, TypeError, ValueError):
        return "Invalid mathematical expression."


def get_order_status(order_id: str) -> dict:
    """Return demo order status data until a real commerce API is connected."""
    fake_db = {
        "1234": "Shipped",
        "5678": "Processing",
        "9999": "Delivered",
    }
    order_id = str(order_id).strip()
    return {"order_id": order_id, "status": fake_db.get(order_id, "Not Found")}


AVAILABLE_FUNCTIONS = {
    "get_time": get_time,
    "get_date": get_date,
    "calculator": calculator,
    "get_order_status": get_order_status,
    "get_weather": get_weather,
    "get_weather_forecast": get_weather_forecast,
    "get_tomorrow_weather": get_tomorrow_weather,
    "get_rain_prediction": get_rain_prediction,
    "web_search": web_search,
    "wikipedia_search": wikipedia_search,
}


TOOL_SCHEMAS = [
    {
        "name": "get_time",
        "description": "Get the current local time.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_date",
        "description": "Get today's date.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "calculator",
        "description": "Calculate a mathematical expression.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to calculate.",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "get_order_status",
        "description": "Check the status of an order using its order ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID."}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get current weather for a city or country.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City or country name."}
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_weather_forecast",
        "description": "Get a five-day weather forecast for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name."}
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_tomorrow_weather",
        "description": "Get tomorrow's weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name."}
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_rain_prediction",
        "description": "Check whether rain is expected for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name."},
                "tomorrow": {
                    "type": "boolean",
                    "description": "Set true to check tomorrow's rain.",
                },
            },
            "required": ["city"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the internet for current or recent information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."},
                "num_results": {
                    "type": "integer",
                    "description": "Number of results, from 1 to 10.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "wikipedia_search",
        "description": "Search Wikipedia for an encyclopedic topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The topic to search for."}
            },
            "required": ["query"],
        },
    },
]
