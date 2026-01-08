"""
config.py
⚙️ Configuration for Dashboard Service
"""
import os
from typing import Dict

class Config:
    """Dashboard configuration"""
    
    # ============ APP CONFIGURATION ============
    APP_TITLE = "⚡ Vietnam Energy Forecasting"
    APP_ICON = "⚡"
    PAGE_LAYOUT = "wide"  # wide or centered
    
    # ============ AWS S3 CONFIGURATION ============
    S3_BUCKET = os.getenv("S3_BUCKET", "vietnam-energy-data")
    AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
    
    # Data paths
    GOLD_PREFIX = "gold/features"
    MODELS_PREFIX = "models"
    PREDICTIONS_PREFIX = "predictions"
    
    # ============ DATA REFRESH ============
    # Cache TTL (seconds)
    CACHE_TTL_CONFIG = None  # Never expire
    CACHE_TTL_DATA = 300  # 5 minutes
    CACHE_TTL_METRICS = 60  # 1 minute
    
    # Auto-refresh interval (seconds)
    AUTO_REFRESH_INTERVAL = 300  # 5 minutes
    
    # ============ DISPLAY CONFIGURATION ============
    # Forecast horizon (hours)
    FORECAST_HOURS = 24
    HISTORICAL_HOURS = 24
    
    # Chart configuration
    CHART_HEIGHT = 400
    CHART_THEME = "plotly_dark"  # plotly, plotly_white, plotly_dark
    
    # Data table
    ROWS_PER_PAGE = 100
    
    # ============ METRICS THRESHOLDS ============
    # Good/bad thresholds
    MAPE_GOOD = 5.0  # MAPE < 5% is good
    MAPE_WARNING = 10.0  # MAPE < 10% is ok
    
    RMSE_GOOD = 50.0  # RMSE < 50 is good
    RMSE_WARNING = 100.0  # RMSE < 100 is ok
    
    R2_GOOD = 0.85  # R² > 0.85 is good
    R2_WARNING = 0.70  # R² > 0.70 is ok
    
    # ============ COLOR SCHEME ============
    COLORS = {
        # Primary colors
        'primary': '#1f77b4',      # Blue
        'secondary': '#ff7f0e',    # Orange
        'tertiary': '#2ca02c',     # Green
        
        # Semantic colors
        'actual': '#1f77b4',       # Blue for actual data
        'forecast': '#ff7f0e',     # Orange for forecast
        'confidence': 'rgba(31,119,180,0.2)',  # Light blue for CI
        
        # Status colors
        'success': '#2ca02c',      # Green
        'warning': '#ff9800',      # Orange
        'danger': '#d62728',       # Red
        'info': '#17a2b8',         # Cyan
        
        # UI colors
        'background': '#0e1117',
        'surface': '#262730',
        'text': '#fafafa',
        'text_secondary': '#a0a0a0'
    }
    
    # ============ KPI ICONS ============
    KPI_ICONS = {
        'current_load': '⚡',
        'peak_load': '📊',
        'trend': '📈',
        'temperature': '🌡️',
        'humidity': '💧'
    }
    
    # ============ MODEL CONFIGURATION ============
    MODEL_TYPE = "xgboost"  # Default model type
    
    @staticmethod
    def get_model_path(version: str = "latest") -> str:
        """Get S3 path for model"""
        return f"{Config.MODELS_PREFIX}/{Config.MODEL_TYPE}/{version}"
    
    @staticmethod
    def get_predictions_path(date: str = "latest") -> str:
        """Get S3 path for predictions"""
        return f"{Config.PREDICTIONS_PREFIX}/{date}/predictions.json"
    
    @staticmethod
    def format_number(value: float, decimals: int = 1) -> str:
        """Format number with thousand separators"""
        return f"{value:,.{decimals}f}"
    
    @staticmethod
    def get_metric_color(metric_name: str, value: float) -> str:
        """
        Get color based on metric value
        
        Args:
            metric_name: Name of metric (mape, rmse, r2)
            value: Metric value
        
        Returns:
            str: Color code
        """
        if metric_name.lower() == 'mape':
            if value <= Config.MAPE_GOOD:
                return Config.COLORS['success']
            elif value <= Config.MAPE_WARNING:
                return Config.COLORS['warning']
            else:
                return Config.COLORS['danger']
        
        elif metric_name.lower() == 'rmse':
            if value <= Config.RMSE_GOOD:
                return Config.COLORS['success']
            elif value <= Config.RMSE_WARNING:
                return Config.COLORS['warning']
            else:
                return Config.COLORS['danger']
        
        elif metric_name.lower() == 'r2':
            if value >= Config.R2_GOOD:
                return Config.COLORS['success']
            elif value >= Config.R2_WARNING:
                return Config.COLORS['warning']
            else:
                return Config.COLORS['danger']
        
        return Config.COLORS['text']
    
    @staticmethod
    def get_metric_status(metric_name: str, value: float) -> str:
        """
        Get status text based on metric value
        
        Args:
            metric_name: Name of metric
            value: Metric value
        
        Returns:
            str: Status text (Good ✅, OK ⚠️, Poor ❌)
        """
        color = Config.get_metric_color(metric_name, value)
        
        if color == Config.COLORS['success']:
            return "Good ✅"
        elif color == Config.COLORS['warning']:
            return "OK ⚠️"
        else:
            return "Poor ❌"