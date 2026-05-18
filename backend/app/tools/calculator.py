"""
Calculator Tool — evaluates math expressions safely.
"""

from langchain_core.tools import tool


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression. Use this for pricing calculations,
    comparisons, percentages, or any math the user needs.
    Examples: '100 * 12', '5000 / 30', '(49.99 - 29.99) / 49.99 * 100'"""
    try:
        # Allow only safe math operations
        allowed_chars = set("0123456789+-*/.() %")
        if not all(c in allowed_chars for c in expression.replace(" ", "")):
            return "Invalid expression. Only numbers and basic math operators allowed."
        result = eval(expression)  # Safe because we validated chars
        return str(round(result, 2))
    except Exception as e:
        return f"Calculation error: {str(e)}"
