"""
models/base_model.py
🤖 Abstract Base Model - Interface cho tất cả ML models
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class ModelMetadata:
    """Metadata cho model"""
    model_type: str
    version: str
    trained_at: str
    training_samples: int
    validation_samples: int
    test_samples: int
    features_count: int
    feature_names: list
    hyperparameters: dict
    
    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class PredictionOutput:
    """Standardized output format cho tất cả models"""
    predictions: np.ndarray          # Shape: (n_samples,)
    timestamps: np.ndarray           # Shape: (n_samples,) datetime64
    confidence_lower: np.ndarray     # Shape: (n_samples,)
    confidence_upper: np.ndarray     # Shape: (n_samples,)
    feature_importance: Dict[str, float]
    metadata: ModelMetadata
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization"""
        return {
            'predictions': self.predictions.tolist(),
            'timestamps': [str(ts) for ts in self.timestamps],
            'confidence_intervals': {
                'lower': self.confidence_lower.tolist(),
                'upper': self.confidence_upper.tolist()
            },
            'feature_importance': self.feature_importance,
            'metadata': self.metadata.to_dict()
        }

class BaseModel(ABC):
    """
    Abstract base class cho tất cả ML models
    
    Mọi model phải implement các methods này
    để đảm bảo tính nhất quán trong pipeline
    """
    
    def __init__(self, model_type: str, hyperparameters: dict = None):
        """
        Args:
            model_type: Loại model (xgboost, lstm, etc.)
            hyperparameters: Dict hyperparameters
        """
        self.model_type = model_type
        self.hyperparameters = hyperparameters or {}
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.is_trained = False
        self.metadata = None
    
    @abstractmethod
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame = None,
        y_val: pd.Series = None
    ) -> Dict[str, float]:
        """
        Train model
        
        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features (optional)
            y_val: Validation target (optional)
        
        Returns:
            Dict[str, float]: Training metrics
        """
        pass
    
    @abstractmethod
    def predict(
        self,
        X: pd.DataFrame,
        return_confidence: bool = True
    ) -> Tuple[np.ndarray, Optional[Tuple[np.ndarray, np.ndarray]]]:
        """
        Generate predictions
        
        Args:
            X: Features DataFrame
            return_confidence: Whether to return confidence intervals
        
        Returns:
            predictions: np.ndarray
            confidence: Tuple[lower, upper] (if return_confidence=True)
        """
        pass
    
    @abstractmethod
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores
        
        Returns:
            Dict[str, float]: {feature_name: importance_score}
        """
        pass
    
    def predict_with_metadata(
        self,
        X: pd.DataFrame,
        timestamps: pd.Series = None
    ) -> PredictionOutput:
        """
        Predict và trả về standardized output
        
        Args:
            X: Features DataFrame
            timestamps: Timestamps tương ứng với predictions
        
        Returns:
            PredictionOutput: Standardized output
        """
        if not self.is_trained:
            raise ValueError("Model chưa được train!")
        
        # Generate predictions
        predictions, (conf_lower, conf_upper) = self.predict(
            X,
            return_confidence=True
        )
        
        # Handle timestamps
        if timestamps is None:
            if 'datetime' in X.columns:
                timestamps = X['datetime'].values
            else:
                # Generate dummy timestamps
                timestamps = pd.date_range(
                    start=datetime.now(),
                    periods=len(predictions),
                    freq='H'
                ).values
        
        # Get feature importance
        feature_importance = self.get_feature_importance()
        
        # Create output
        output = PredictionOutput(
            predictions=predictions,
            timestamps=timestamps,
            confidence_lower=conf_lower,
            confidence_upper=conf_upper,
            feature_importance=feature_importance,
            metadata=self.metadata
        )
        
        return output
    
    def save_metadata(
        self,
        version: str,
        train_size: int,
        val_size: int,
        test_size: int,
        feature_names: list
    ):
        """
        Save model metadata
        
        Args:
            version: Model version
            train_size: Number of training samples
            val_size: Number of validation samples
            test_size: Number of test samples
            feature_names: List of feature names
        """
        self.metadata = ModelMetadata(
            model_type=self.model_type,
            version=version,
            trained_at=datetime.utcnow().isoformat(),
            training_samples=train_size,
            validation_samples=val_size,
            test_samples=test_size,
            features_count=len(feature_names),
            feature_names=feature_names,
            hyperparameters=self.hyperparameters
        )
    
    def validate_input(self, X: pd.DataFrame):
        """
        Validate input DataFrame
        
        Args:
            X: Input features
        
        Raises:
            ValueError: If input is invalid
        """
        if X is None or len(X) == 0:
            raise ValueError("Input DataFrame is empty")
        
        if self.feature_names is not None:
            missing_features = set(self.feature_names) - set(X.columns)
            if missing_features:
                raise ValueError(f"Missing features: {missing_features}")
            
            extra_features = set(X.columns) - set(self.feature_names)
            if extra_features:
                # Just log warning, không raise error
                print(f"⚠️ Extra features will be ignored: {extra_features}")
    
    def __repr__(self) -> str:
        status = "Trained" if self.is_trained else "Not Trained"
        return f"{self.model_type.upper()} Model ({status})"