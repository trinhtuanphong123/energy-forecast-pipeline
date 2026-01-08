"""
data/splitter.py
✂️ Train/Val/Test Split cho Time Series
"""
import pandas as pd
import numpy as np
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

class DataSplitter:
    """Split data into train/val/test sets for time series"""
    
    @staticmethod
    def time_series_split(
        X: pd.DataFrame,
        y: pd.Series,
        timestamps: pd.DatetimeIndex = None,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ) -> Tuple:
        """
        Time-series split (sequential, no shuffle)
        
        Args:
            X: Features DataFrame
            y: Target Series
            timestamps: DatetimeIndex (optional)
            train_ratio: Training set ratio
            val_ratio: Validation set ratio
            test_ratio: Test set ratio
        
        Returns:
            Tuple: (X_train, X_val, X_test, y_train, y_val, y_test, 
                   ts_train, ts_val, ts_test)
        """
        logger.info("✂️ Splitting data (time-series sequential)...")
        
        # Validate ratios
        total = train_ratio + val_ratio + test_ratio
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Ratios must sum to 1.0, got {total}")
        
        n = len(X)
        train_size = int(n * train_ratio)
        val_size = int(n * val_ratio)
        
        # Split indices
        train_end = train_size
        val_end = train_size + val_size
        
        # Split features and target
        X_train = X.iloc[:train_end].copy()
        y_train = y.iloc[:train_end].copy()
        
        X_val = X.iloc[train_end:val_end].copy()
        y_val = y.iloc[train_end:val_end].copy()
        
        X_test = X.iloc[val_end:].copy()
        y_test = y.iloc[val_end:].copy()
        
        # Split timestamps if provided
        if timestamps is not None:
            ts_train = timestamps[:train_end]
            ts_val = timestamps[train_end:val_end]
            ts_test = timestamps[val_end:]
        else:
            ts_train = ts_val = ts_test = None
        
        # Log info
        logger.info(f"  Train: {len(X_train)} samples")
        logger.info(f"  Val: {len(X_val)} samples")
        logger.info(f"  Test: {len(X_test)} samples")
        
        if timestamps is not None:
            logger.info(f"  Train period: {ts_train[0]} to {ts_train[-1]}")
            logger.info(f"  Val period: {ts_val[0]} to {ts_val[-1]}")
            logger.info(f"  Test period: {ts_test[0]} to {ts_test[-1]}")
        
        return X_train, X_val, X_test, y_train, y_val, y_test, ts_train, ts_val, ts_test
    
    @staticmethod
    def get_split_info(
        X_train: pd.DataFrame,
        X_val: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_val: pd.Series,
        y_test: pd.Series
    ) -> dict:
        """
        Get detailed split information
        
        Returns:
            dict: Split statistics
        """
        return {
            'train': {
                'samples': len(X_train),
                'features': len(X_train.columns),
                'target_mean': y_train.mean(),
                'target_std': y_train.std()
            },
            'val': {
                'samples': len(X_val),
                'features': len(X_val.columns),
                'target_mean': y_val.mean(),
                'target_std': y_val.std()
            },
            'test': {
                'samples': len(X_test),
                'features': len(X_test.columns),
                'target_mean': y_test.mean(),
                'target_std': y_test.std()
            }
        }