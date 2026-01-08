"""
features/base.py
🧠 Base Feature Engineering Interface (Strategy Pattern)
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class BaseFeatureStrategy(ABC):
    """
    Abstract base class cho feature engineering strategies
    
    Mỗi strategy tạo features phù hợp với model type
    (XGBoost, LSTM, Prophet, etc.)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Args:
            config: Feature engineering configuration
        """
        self.config = config or {}
        self.feature_names = []
    
    @abstractmethod
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo features từ canonical data
        
        Args:
            df: Input canonical DataFrame (đã có base features)
        
        Returns:
            pd.DataFrame: DataFrame với additional features
        """
        pass
    
    @abstractmethod
    def get_feature_info(self) -> Dict[str, Any]:
        """
        Get info về features đã tạo
        
        Returns:
            dict: Feature information
        """
        pass
    
    def validate_input(self, df: pd.DataFrame) -> bool:
        """
        Validate input DataFrame
        
        Args:
            df: Input DataFrame
        
        Returns:
            bool: True if valid
        
        Raises:
            ValueError: If validation fails
        """
        if df is None or len(df) == 0:
            raise ValueError("Input DataFrame is empty")
        
        return True
    
    def get_feature_count(self) -> int:
        """Get number of features created"""
        return len(self.feature_names)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(features={self.get_feature_count()})"