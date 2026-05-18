"""
DateTime Tool — returns current date and time.
"""

from datetime import datetime
from langchain_core.tools import tool


@tool
def get_datetime() -> str:
    """Get the current date and time. Use this when the user asks about
    the current date, time, day of the week, etc."""
    now = datetime.now()
    return now.strftime("Current date: %A, %B %d, %Y. Current time: %I:%M %p")
