"""
evaluation/metrics.py
📈 Evaluation Metrics
"""
import numpy as np
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score
)
from typing import Dict

def calculate_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Square Error"""
    return np.sqrt(mean_squared_error(y_true, y_pred))

def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Percentage Error"""
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

def calculate_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Error"""
    return mean_absolute_error(y_true, y_pred)

def calculate_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """R-squared Score"""
    return r2_score(y_true, y_pred)

def calculate_forecast_bias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Forecast Bias (average difference)"""
    return np.mean(y_pred - y_true)

def calculate_all_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate tất cả metrics"""
    return {
        'rmse': calculate_rmse(y_true, y_pred),
        'mape': calculate_mape(y_true, y_pred),
        'mae': calculate_mae(y_true, y_pred),
        'r2': calculate_r2(y_true, y_pred),
        'forecast_bias': calculate_forecast_bias(y_true, y_pred)
    }