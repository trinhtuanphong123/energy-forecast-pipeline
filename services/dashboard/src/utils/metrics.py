"""
utils/metrics.py
📊 Metrics Calculation
"""
import numpy as np
from typing import Dict

class MetricsCalculator:
    """Calculate various metrics"""
    
    @staticmethod
    def calculate_mape(actual, predicted) -> float:
        """Mean Absolute Percentage Error"""
        actual = np.array(actual)
        predicted = np.array(predicted)
        return np.mean(np.abs((actual - predicted) / actual)) * 100
    
    @staticmethod
    def calculate_rmse(actual, predicted) -> float:
        """Root Mean Square Error"""
        actual = np.array(actual)
        predicted = np.array(predicted)
        return np.sqrt(np.mean((actual - predicted) ** 2))
    
    @staticmethod
    def calculate_mae(actual, predicted) -> float:
        """Mean Absolute Error"""
        actual = np.array(actual)
        predicted = np.array(predicted)
        return np.mean(np.abs(actual - predicted))
    
    @staticmethod
    def calculate_r2(actual, predicted) -> float:
        """R-squared Score"""
        actual = np.array(actual)
        predicted = np.array(predicted)
        ss_res = np.sum((actual - predicted) ** 2)
        ss_tot = np.sum((actual - np.mean(actual)) ** 2)
        return 1 - (ss_res / ss_tot)