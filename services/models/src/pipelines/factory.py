"""
pipelines/factory.py
🏭 Model Pipeline Factory
"""
import logging
from typing import Dict, Any
from .wrappers.xgboost_pkg import XGBoostModelWrapper

logger = logging.getLogger(__name__)

class ModelPipelineFactory:
    """
    Factory để tạo model pipelines
    """
    
    _pipelines = {
        'xgboost': XGBoostModelWrapper,
        # Future:
        # 'lstm': LSTMModelWrapper,
        # 'random_forest': RandomForestModelWrapper,
    }
    
    @classmethod
    def create_pipeline(
        cls,
        model_type: str,
        hyperparameters: Dict[str, Any] = None
    ):
        """
        Tạo model pipeline
        
        Args:
            model_type: Type of model
            hyperparameters: Model hyperparameters
        
        Returns:
            Model pipeline wrapper
        
        Raises:
            ValueError: If model type not supported
        """
        model_type = model_type.lower()
        
        if model_type not in cls._pipelines:
            available = ', '.join(cls._pipelines.keys())
            raise ValueError(
                f"Unknown model type: {model_type}. "
                f"Available: {available}"
            )
        
        pipeline_class = cls._pipelines[model_type]
        
        logger.info(f"🏭 Creating {model_type} pipeline...")
        pipeline = pipeline_class(hyperparameters=hyperparameters)
        
        return pipeline
    
    @classmethod
    def register_pipeline(cls, name: str, pipeline_class: type):
        """Register new pipeline"""
        cls._pipelines[name] = pipeline_class
        logger.info(f"✅ Registered pipeline: {name}")
    
    @classmethod
    def get_available_pipelines(cls) -> list:
        """Get available pipelines"""
        return list(cls._pipelines.keys())