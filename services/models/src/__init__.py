# src/__init__.py
"""
Vietnam Energy Forecasting - Training Service
Machine Learning Model Training Pipeline
"""
__version__ = "1.0.0"

# src/data/__init__.py
"""
Data Module - Data loading and preprocessing
"""
from .loader import DataLoader
from .preprocessor import DataPreprocessor
from .splitter import DataSplitter

__all__ = [
    'DataLoader',
    'DataPreprocessor',
    'DataSplitter'
]

# src/models/__init__.py
"""
Models Module - ML model implementations
"""
from .base_model import BaseModel, ModelMetadata, PredictionOutput
from .xgboost_model import XGBoostModel
from .model_factory import ModelFactory

__all__ = [
    'BaseModel',
    'ModelMetadata',
    'PredictionOutput',
    'XGBoostModel',
    'ModelFactory'
]

# src/training/__init__.py
"""
Training Module - Training logic and utilities
"""
from .trainer import ModelTrainer
from .hyperparameter import HyperparameterTuner
from .callbacks import (
    TrainingCallback,
    EarlyStoppingCallback,
    LoggingCallback,
    MetricTrackerCallback,
    CheckpointCallback,
    CallbackList
)

__all__ = [
    'ModelTrainer',
    'HyperparameterTuner',
    'TrainingCallback',
    'EarlyStoppingCallback',
    'LoggingCallback',
    'MetricTrackerCallback',
    'CheckpointCallback',
    'CallbackList'
]

# src/evaluation/__init__.py
"""
Evaluation Module - Metrics and validation
"""
from .metrics import (
    calculate_rmse,
    calculate_mape,
    calculate_mae,
    calculate_r2,
    calculate_forecast_bias,
    calculate_all_metrics
)
from .validator import ModelValidator

__all__ = [
    'calculate_rmse',
    'calculate_mape',
    'calculate_mae',
    'calculate_r2',
    'calculate_forecast_bias',
    'calculate_all_metrics',
    'ModelValidator'
]

# src/storage/__init__.py
"""
Storage Module - Model persistence and versioning
"""
from .model_registry import ModelRegistry
from .metadata import (
    TrainingMetadata,
    ModelMetadata,
    MetadataManager
)

__all__ = [
    'ModelRegistry',
    'TrainingMetadata',
    'ModelMetadata',
    'MetadataManager'
]