"""
models/model_factory.py
🏭 Model Factory - Create models dynamically
"""
import logging
from typing import Dict, Any
from .base_model import BaseModel
from .xgboost_model import XGBoostModel

logger = logging.getLogger(__name__)

class ModelFactory:
    """
    Factory để tạo models dựa trên type
    Hỗ trợ thêm model mới dễ dàng
    """
    
    # Registry of available models
    _models = {
        'xgboost': XGBoostModel,
        # Future models
        # 'lstm': LSTMModel,
        # 'random_forest': RandomForestModel,
        # 'prophet': ProphetModel,
    }
    
    @classmethod
    def create_model(
        cls,
        model_type: str,
        hyperparameters: Dict[str, Any] = None
    ) -> BaseModel:
        """
        Tạo model instance dựa trên type
        
        Args:
            model_type: Type of model (xgboost, lstm, etc.)
            hyperparameters: Model hyperparameters
        
        Returns:
            BaseModel: Model instance
        
        Raises:
            ValueError: If model_type not supported
        """
        model_type = model_type.lower()
        
        if model_type not in cls._models:
            available = ', '.join(cls._models.keys())
            raise ValueError(
                f"Unknown model type: {model_type}. "
                f"Available models: {available}"
            )
        
        model_class = cls._models[model_type]
        
        logger.info(f"🏭 Creating {model_type} model...")
        model = model_class(hyperparameters=hyperparameters)
        
        return model
    
    @classmethod
    def register_model(cls, model_type: str, model_class: type):
        """
        Register new model type
        
        Args:
            model_type: Name of model type
            model_class: Model class (must inherit from BaseModel)
        """
        if not issubclass(model_class, BaseModel):
            raise TypeError(f"{model_class} must inherit from BaseModel")
        
        cls._models[model_type] = model_class
        logger.info(f"✅ Registered new model type: {model_type}")
    
    @classmethod
    def get_available_models(cls) -> list:
        """
        Get list of available model types
        
        Returns:
            list: Available model types
        """
        return list(cls._models.keys())
    
    @classmethod
    def model_exists(cls, model_type: str) -> bool:
        """
        Check if model type exists
        
        Args:
            model_type: Model type to check
        
        Returns:
            bool: True if exists
        """
        return model_type.lower() in cls._models