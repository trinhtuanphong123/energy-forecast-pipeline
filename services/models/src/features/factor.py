"""
features/factory.py
🏭 Feature Strategy Factory
"""
import logging
from typing import Dict, Any
from .base import BaseFeatureStrategy
from .strategies.xgboost import XGBoostFeatureStrategy

logger = logging.getLogger(__name__)

class FeatureStrategyFactory:
    """
    Factory để tạo feature engineering strategies
    """
    
    _strategies = {
        'xgboost': XGBoostFeatureStrategy,
        # Future strategies:
        # 'lstm': LSTMFeatureStrategy,
        # 'prophet': ProphetFeatureStrategy,
    }
    
    @classmethod
    def create_strategy(
        cls,
        strategy_type: str,
        config: Dict[str, Any] = None
    ) -> BaseFeatureStrategy:
        """
        Tạo feature strategy instance
        
        Args:
            strategy_type: Type of strategy ('xgboost', 'lstm', etc.)
            config: Strategy configuration
        
        Returns:
            BaseFeatureStrategy: Strategy instance
        
        Raises:
            ValueError: If strategy type not supported
        """
        strategy_type = strategy_type.lower()
        
        if strategy_type not in cls._strategies:
            available = ', '.join(cls._strategies.keys())
            raise ValueError(
                f"Unknown feature strategy: {strategy_type}. "
                f"Available: {available}"
            )
        
        strategy_class = cls._strategies[strategy_type]
        
        logger.info(f"🏭 Creating {strategy_type} feature strategy...")
        strategy = strategy_class(config=config)
        
        return strategy
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: type):
        """
        Register new feature strategy
        
        Args:
            name: Strategy name
            strategy_class: Strategy class (must inherit from BaseFeatureStrategy)
        """
        if not issubclass(strategy_class, BaseFeatureStrategy):
            raise TypeError(
                f"{strategy_class} must inherit from BaseFeatureStrategy"
            )
        
        cls._strategies[name] = strategy_class
        logger.info(f"✅ Registered feature strategy: {name}")
    
    @classmethod
    def get_available_strategies(cls) -> list:
        """Get list of available strategies"""
        return list(cls._strategies.keys())
    
    @classmethod
    def strategy_exists(cls, strategy_type: str) -> bool:
        """Check if strategy exists"""
        return strategy_type.lower() in cls._strategies