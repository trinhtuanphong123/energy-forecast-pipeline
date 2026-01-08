"""
training/trainer.py
🏋️ Training Pipeline Manager
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd

from .callbacks import CallbackList, LoggingCallback, EarlyStoppingCallback

logger = logging.getLogger(__name__)

class ModelTrainer:
    """
    High-level training pipeline manager
    Coordinates data loading, training, evaluation
    """
    
    def __init__(
        self,
        model,
        config: Dict[str, Any],
        callbacks: list = None
    ):
        """
        Args:
            model: Model instance
            config: Training configuration
            callbacks: List of callbacks
        """
        self.model = model
        self.config = config
        
        # Setup callbacks
        self.callbacks = CallbackList(callbacks or [])
        
        # Add default callbacks
        if not any(isinstance(cb, LoggingCallback) for cb in self.callbacks.callbacks):
            self.callbacks.add(LoggingCallback())
        
        self.training_history = {}
        self.start_time = None
        self.end_time = None
    
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame = None,
        y_val: pd.Series = None
    ) -> Dict[str, float]:
        """
        Execute training pipeline
        
        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features
            y_val: Validation target
        
        Returns:
            Dict: Training metrics
        """
        logger.info("🏋️ Starting training pipeline...")
        
        # Record start time
        self.start_time = datetime.utcnow()
        
        # Call on_train_begin
        self.callbacks.on_train_begin(
            model=self.model,
            X_train=X_train,
            y_train=y_train
        )
        
        try:
            # Train model
            metrics = self.model.train(X_train, y_train, X_val, y_val)
            
            # Store history
            self.training_history = metrics
            
            # Record end time
            self.end_time = datetime.utcnow()
            
            # Call on_train_end
            self.callbacks.on_train_end(
                model=self.model,
                metrics=metrics
            )
            
            logger.info("✅ Training pipeline completed")
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Training pipeline failed: {e}", exc_info=True)
            raise
    
    def train_with_cv(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = 5
    ) -> Dict[str, float]:
        """
        Train with cross-validation
        
        Args:
            X: All features
            y: All targets
            n_splits: Number of CV folds
        
        Returns:
            Dict: Aggregated CV metrics
        """
        logger.info(f"🏋️ Training with {n_splits}-fold cross-validation...")
        
        from evaluation.validator import ModelValidator
        
        validator = ModelValidator(n_splits=n_splits)
        cv_metrics = validator.cross_validate(self.model, X, y)
        
        logger.info("✅ Cross-validation completed")
        
        return cv_metrics
    
    def get_training_duration(self) -> float:
        """
        Get training duration in seconds
        
        Returns:
            float: Duration in seconds
        """
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def get_training_summary(self) -> str:
        """
        Get training summary report
        
        Returns:
            str: Formatted summary
        """
        if not self.training_history:
            return "No training history available"
        
        summary = []
        summary.append("=" * 70)
        summary.append("TRAINING SUMMARY")
        summary.append("=" * 70)
        
        if self.start_time:
            summary.append(f"Started: {self.start_time.isoformat()}")
        if self.end_time:
            summary.append(f"Completed: {self.end_time.isoformat()}")
            duration = self.get_training_duration()
            summary.append(f"Duration: {duration:.1f}s")
        
        summary.append("")
        summary.append("Metrics:")
        for metric, value in self.training_history.items():
            summary.append(f"  {metric}: {value:.4f}")
        
        return "\n".join(summary)