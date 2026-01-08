"""
data/processor.py
🔧 Data Processing Utilities
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    """Process and transform data for visualization"""
    
    @staticmethod
    def prepare_forecast_data(
        predictions: Dict,
        historical: pd.DataFrame,
        hours_ahead: int = 24
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare historical and forecast data separately
        
        Args:
            predictions: Predictions dict
            historical: Historical dataframe
            hours_ahead: Hours to forecast
        
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (historical_df, forecast_df)
        """
        # Extract predictions
        pred_values = predictions.get('predictions', [])[:hours_ahead]
        timestamps = pd.to_datetime(predictions.get('timestamps', []))[:hours_ahead]
        
        # Create forecast dataframe
        forecast_df = pd.DataFrame({
            'datetime': timestamps,
            'value': pred_values
        })
        
        # Prepare historical (last 24h)
        hist_df = pd.DataFrame()
        if historical is not None and not historical.empty:
            hist_df = historical.tail(24).copy()
            
            # Find target column
            target_col = None
            for col in ['electricity_demand', 'total_load', 'load']:
                if col in hist_df.columns:
                    target_col = col
                    break
            
            if target_col:
                hist_df = pd.DataFrame({
                    'datetime': hist_df['datetime'],
                    'value': hist_df[target_col]
                })
        
        return hist_df, forecast_df
    
    @staticmethod
    def calculate_daily_stats(data: pd.DataFrame, column: str = 'value') -> Dict:
        """
        Calculate daily statistics
        
        Args:
            data: DataFrame with value column
            column: Column name to calculate stats
        
        Returns:
            Dict: Statistics
        """
        if data.empty or column not in data.columns:
            return {
                'min': 0,
                'max': 0,
                'mean': 0,
                'std': 0,
                'median': 0
            }
        
        return {
            'min': float(data[column].min()),
            'max': float(data[column].max()),
            'mean': float(data[column].mean()),
            'std': float(data[column].std()),
            'median': float(data[column].median())
        }
    
    @staticmethod
    def calculate_trend(
        current_value: float,
        forecast_values: List[float],
        hours: int = 24
    ) -> Dict:
        """
        Calculate trend metrics
        
        Args:
            current_value: Current load value
            forecast_values: List of forecast values
            hours: Number of hours to consider
        
        Returns:
            Dict: Trend metrics
        """
        if not forecast_values or current_value == 0:
            return {
                'avg_forecast': 0,
                'change_abs': 0,
                'change_pct': 0,
                'direction': 'neutral'
            }
        
        values = forecast_values[:hours]
        avg_forecast = sum(values) / len(values)
        change_abs = avg_forecast - current_value
        change_pct = (change_abs / current_value) * 100
        
        direction = 'up' if change_pct > 1 else 'down' if change_pct < -1 else 'stable'
        
        return {
            'avg_forecast': avg_forecast,
            'change_abs': change_abs,
            'change_pct': change_pct,
            'direction': direction
        }
    
    @staticmethod
    def find_peak_load(forecast_values: List[float], timestamps: List) -> Tuple[float, str]:
        """
        Find peak load in forecast
        
        Args:
            forecast_values: List of forecast values
            timestamps: List of timestamps
        
        Returns:
            Tuple: (peak_value, peak_time)
        """
        if not forecast_values:
            return 0, "N/A"
        
        peak_idx = np.argmax(forecast_values)
        peak_value = forecast_values[peak_idx]
        
        if timestamps and len(timestamps) > peak_idx:
            peak_time = pd.to_datetime(timestamps[peak_idx]).strftime("%Y-%m-%d %H:%M")
        else:
            peak_time = "N/A"
        
        return peak_value, peak_time
    
    @staticmethod
    def filter_features_by_importance(
        feature_importance: Dict,
        threshold: float = 0.01,
        top_n: int = None
    ) -> Dict:
        """
        Filter features by importance
        
        Args:
            feature_importance: Dict of {feature: importance}
            threshold: Minimum importance threshold
            top_n: Return only top N features
        
        Returns:
            Dict: Filtered features
        """
        # Filter by threshold
        filtered = {k: v for k, v in feature_importance.items() if v >= threshold}
        
        # Sort by importance
        sorted_features = dict(sorted(filtered.items(), key=lambda x: x[1], reverse=True))
        
        # Return top N if specified
        if top_n:
            sorted_features = dict(list(sorted_features.items())[:top_n])
        
        return sorted_features