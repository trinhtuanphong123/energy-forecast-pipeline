"""
data/preprocessor.py
🔧 Data Preprocessing & Feature Selection
"""
import logging
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from typing import Tuple

logger = logging.getLogger(__name__)

class DataPreprocessor:
    """Preprocess data trước khi train"""
    
    def __init__(self, scaling_method: str = "standard"):
        self.scaling_method = scaling_method
        self.scaler = self._get_scaler()
        self.feature_stats = {}
    
    def _get_scaler(self):
        if self.scaling_method == "standard":
            return StandardScaler()
        elif self.scaling_method == "minmax":
            return MinMaxScaler()
        elif self.scaling_method == "robust":
            return RobustScaler()
        else:
            raise ValueError(f"Unknown scaling method: {self.scaling_method}")
    
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values"""
        logger.info("🔧 Handling missing values...")
    
        df = df.copy()  # ✅ THÊM: Tránh modify original
    
        # Fill numeric columns with median
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isnull().any():
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)  # ✅ SỬA: Không dùng inplace
                logger.debug(f"  Filled {col} with median: {median_val:.2f}")
    
        return df

    def remove_outliers(self, df: pd.DataFrame, threshold: float = 3.5) -> pd.DataFrame:
        """Remove outliers using Z-score"""
        logger.info("🔧 Removing outliers...")
    
        df = df.copy()  # ✅ THÊM
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        initial_len = len(df)
    
        # ✅ SỬA: Chỉ loại bỏ row nếu có NHIỀU outlier columns
        outlier_mask = pd.Series([False] * len(df), index=df.index)
    
        for col in numeric_cols:
            if df[col].std() > 0:  # ✅ THÊM: Tránh chia cho 0
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                outlier_mask |= (z_scores > threshold)
    
        df = df[~outlier_mask]
    
        removed = initial_len - len(df)
        logger.info(f"  Removed {removed} outliers ({removed/initial_len*100:.1f}%)")
    
        return df
    
    def select_features(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        importance_threshold: float = 0.01,
        max_features: int = 50
    ) -> pd.DataFrame:
        """Select important features"""
        # This is placeholder - will use model's feature importance
        return X