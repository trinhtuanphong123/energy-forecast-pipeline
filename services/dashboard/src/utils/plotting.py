"""
utils/plotting.py
📈 Plotting Utilities
"""
from typing import Dict

def create_plotly_theme(dark_mode: bool = True) -> str:
    """
    Get Plotly theme name
    
    Args:
        dark_mode: Use dark theme
    
    Returns:
        str: Theme name
    """
    return "plotly_dark" if dark_mode else "plotly_white"

def get_chart_config() -> Dict:
    """Get Plotly chart config"""
    return {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': [
            'lasso2d',
            'select2d',
            'autoScale2d'
        ]
    }