"""
features/strategies/xgboost.py
🌳 XGBoost Feature Engineering Strategy
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from ..base import BaseFeatureStrategy

logger = logging.getLogger(__name__)

class XGBoostFeatureStrategy(BaseFeatureStrategy):
    """
    Feature engineering strategy cho XGBoost
    
    Tạo:
    - Lag features
    - Rolling statistics
    - Feature interactions (optional)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # Config defaults
        self.create_lags = config.get('create_lags', True)
        self.lag_periods = config.get('lag_periods', [1, 2, 3, 24, 168])
        
        self.create_rolling = config.get('create_rolling', True)
        self.rolling_windows = config.get('rolling_windows', [3, 6, 12, 24])
        
        self.create_interactions = config.get('create_interactions', False)
        
        self.target_column = None
        self.created_features = []
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo XGBoost features từ canonical data
        
        Args:
            df: Canonical DataFrame (đã có base features từ Processing)
        
        Returns:
            pd.DataFrame: DataFrame với lag và rolling features
        """
        logger.info("🌳 Creating XGBoost features...")
        
        self.validate_input(df)
        
        df_features = df.copy()
        self.created_features = []
        
        # Identify numeric columns for feature engineering
        numeric_cols = df_features.select_dtypes(include=[np.number]).columns.tolist()
        
        # Exclude metadata columns
        exclude = ['query_date', 'processed_at', 'signal']
        numeric_cols = [col for col in numeric_cols if col not in exclude]
        
        logger.info(f"  Base numeric columns: {len(numeric_cols)}")
        
        # 1. LAG FEATURES
        if self.create_lags:
            df_features = self._create_lag_features(df_features, numeric_cols)
        
        # 2. ROLLING STATISTICS
        if self.create_rolling:
            df_features = self._create_rolling_features(df_features, numeric_cols)
        
        # 3. FEATURE INTERACTIONS (optional)
        if self.create_interactions:
            df_features = self._create_interaction_features(df_features)
        
        # Drop rows with NaN created by lag/rolling
        initial_len = len(df_features)
        df_features = df_features.dropna()
        dropped = initial_len - len(df_features)
        
        if dropped > 0:
            logger.info(f"  Dropped {dropped} rows with NaN from lag/rolling")
        
        logger.info(f"✅ Created {len(self.created_features)} new features")
        logger.info(f"  Total features: {len(df_features.columns)}")
        
        self.feature_names = self.created_features
        
        return df_features
    
    def _create_lag_features(
        self,
        df: pd.DataFrame,
        columns: List[str]
    ) -> pd.DataFrame:
        """Tạo lag features"""
        logger.info(f"  Creating lag features (periods={self.lag_periods})...")
        
        for col in columns:
            for lag in self.lag_periods:
                feature_name = f"{col}_lag_{lag}"
                df[feature_name] = df[col].shift(lag)
                self.created_features.append(feature_name)
        
        logger.info(f"    ✅ Created {len(columns) * len(self.lag_periods)} lag features")
        
        return df
    
    def _create_rolling_features(
        self,
        df: pd.DataFrame,
        columns: List[str]
    ) -> pd.DataFrame:
        """Tạo rolling statistics features"""
        logger.info(f"  Creating rolling features (windows={self.rolling_windows})...")
        
        for col in columns:
            for window in self.rolling_windows:
                # Rolling mean
                feature_name = f"{col}_rolling_mean_{window}"
                df[feature_name] = df[col].rolling(window=window).mean()
                self.created_features.append(feature_name)
                
                # Rolling std
                feature_name = f"{col}_rolling_std_{window}"
                df[feature_name] = df[col].rolling(window=window).std()
                self.created_features.append(feature_name)
        
        total = len(columns) * len(self.rolling_windows) * 2  # mean + std
        logger.info(f"    ✅ Created {total} rolling features")
        
        return df
    
    def _create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo interaction features (multiplicative)
        
        VD: temperature * hour_sin, temperature * is_weekend
        """
        logger.info(f"  Creating interaction features...")
        
        # Define key interaction pairs
        interactions = [
            ('temperature', 'hour_sin'),
            ('temperature', 'is_weekend'),
            ('humidity', 'temperature'),
        ]
        
        count = 0
        for col1, col2 in interactions:
            if col1 in df.columns and col2 in df.columns:
                feature_name = f"{col1}_x_{col2}"
                df[feature_name] = df[col1] * df[col2]
                self.created_features.append(feature_name)
                count += 1
        
        logger.info(f"    ✅ Created {count} interaction features")
        
        return df
    
    def get_feature_info(self) -> Dict[str, Any]:
        """Get feature info"""
        return {
            'strategy': 'xgboost',
            'total_features': len(self.created_features),
            'lag_features': len([f for f in self.created_features if '_lag_' in f]),
            'rolling_features': len([f for f in self.created_features if '_rolling_' in f]),
            'interaction_features': len([f for f in self.created_features if '_x_' in f]),
            'config': {
                'lag_periods': self.lag_periods,
                'rolling_windows': self.rolling_windows,
                'interactions_enabled': self.create_interactions
            }
        }