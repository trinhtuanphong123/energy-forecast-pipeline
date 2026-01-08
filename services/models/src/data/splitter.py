"""
data/splitter.py
✂️ Train/Val/Test Split
"""
import pandas as pd
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

class DataSplitter:
    """Split data into train/val/test sets"""
    
    @staticmethod
    def time_series_split(
        X: pd.DataFrame,
        y: pd.Series,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ) -> Tuple:
        """
        Time-series split (không shuffle)
        
        Returns:
            X_train, X_val, X_test, y_train, y_val, y_test
        """
        logger.info("✂️ Splitting data (time-series)...")
        
        n = len(X)
        train_size = int(n * train_ratio)
        val_size = int(n * val_ratio)
        
        # Split
        X_train = X.iloc[:train_size]
        y_train = y.iloc[:train_size]
        
        X_val = X.iloc[train_size:train_size+val_size]
        y_val = y.iloc[train_size:train_size+val_size]
        
        X_test = X.iloc[train_size+val_size:]
        y_test = y.iloc[train_size+val_size:]
        
        logger.info(f"  Train: {len(X_train)} samples")
        logger.info(f"  Val: {len(X_val)} samples")
        logger.info(f"  Test: {len(X_test)} samples")
        
        return X_train, X_val, X_test, y_train, y_val, y_test  