"""
utils/formatting.py
✨ Formatting Utilities
"""
from datetime import datetime

def format_number(value: float, decimals: int = 1) -> str:
    """Format number with thousand separators"""
    return f"{value:,.{decimals}f}"

def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime"""
    return dt.strftime(format)

def format_percentage(value: float, decimals: int = 1) -> str:
    """Format as percentage"""
    return f"{value:.{decimals}f}%"