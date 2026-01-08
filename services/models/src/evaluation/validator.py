"""
evaluation/validator.py
✅ Cross-Validation for Model Evaluation
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from sklearn.model_selection import TimeSeriesSplit

from .metrics import calculate_all_metrics

logger = logging.getLogger(__name__)

class ModelValidator:
    """
    Cross-validation cho time-series models
    """
    
    def __init__(self, n_splits: int = 5):
        """
        Args:
            n_splits: Số folds cho cross-validation
        """
        self.n_splits = n_splits
        self.cv_results = []
    
    def cross_validate(
        self,
        model,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Dict[str, float]:
        """
        Perform time-series cross-validation
        
        Args:
            model: Model instance (phải có fit() và predict())
            X: Features DataFrame
            y: Target Series
        
        Returns:
            Dict: Aggregated metrics across folds
        """
        logger.info(f"✅ Running {self.n_splits}-fold time-series cross-validation...")
        
        # Time series split (không shuffle)
        tscv = TimeSeriesSplit(n_splits=self.n_splits)
        
        fold_metrics = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
            logger.info(f"  Fold {fold}/{self.n_splits}")
            
            # Split data
            X_train_fold = X.iloc[train_idx]
            y_train_fold = y.iloc[train_idx]
            X_val_fold = X.iloc[val_idx]
            y_val_fold = y.iloc[val_idx]
            
            try:
                # Train model on fold
                model.train(X_train_fold, y_train_fold)
                
                # Predict on validation fold
                y_pred, _ = model.predict(X_val_fold, return_confidence=False)
                
                # Calculate metrics
                metrics = calculate_all_metrics(y_val_fold.values, y_pred)
                fold_metrics.append(metrics)
                
                logger.info(f"    RMSE: {metrics['rmse']:.2f}, MAPE: {metrics['mape']:.2f}%")
                
            except Exception as e:
                logger.error(f"    ❌ Fold {fold} failed: {e}")
                continue
        
        if not fold_metrics:
            raise ValueError("All cross-validation folds failed!")
        
        # Aggregate metrics across folds
        aggregated = self._aggregate_metrics(fold_metrics)
        
        logger.info(f"✅ Cross-validation completed:")
        logger.info(f"  Mean RMSE: {aggregated['rmse_mean']:.2f} ± {aggregated['rmse_std']:.2f}")
        logger.info(f"  Mean MAPE: {aggregated['mape_mean']:.2f}% ± {aggregated['mape_std']:.2f}%")
        
        self.cv_results = fold_metrics
        
        return aggregated
    
    def _aggregate_metrics(self, fold_metrics: List[Dict]) -> Dict[str, float]:
        """
        Aggregate metrics from all folds
        
        Args:
            fold_metrics: List of metric dicts from each fold
        
        Returns:
            Dict: Mean and std for each metric
        """
        aggregated = {}
        
        # Get all metric names
        metric_names = fold_metrics[0].keys()
        
        for metric_name in metric_names:
            values = [fold[metric_name] for fold in fold_metrics]
            
            aggregated[f'{metric_name}_mean'] = np.mean(values)
            aggregated[f'{metric_name}_std'] = np.std(values)
            aggregated[f'{metric_name}_min'] = np.min(values)
            aggregated[f'{metric_name}_max'] = np.max(values)
        
        return aggregated
    
    def get_fold_results(self) -> pd.DataFrame:
        """
        Get detailed results for each fold
        
        Returns:
            pd.DataFrame: Results table
        """
        if not self.cv_results:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.cv_results)
        df.index.name = 'fold'
        return df
    
    def validate_predictions(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        confidence_lower: np.ndarray = None,
        confidence_upper: np.ndarray = None
    ) -> Dict[str, float]:
        """
        Validate predictions quality
        
        Args:
            y_true: True values
            y_pred: Predictions
            confidence_lower: Lower bound of confidence interval
            confidence_upper: Upper bound of confidence interval
        
        Returns:
            Dict: Validation metrics
        """
        validation_metrics = {}
        
        # Basic metrics
        basic_metrics = calculate_all_metrics(y_true, y_pred)
        validation_metrics.update(basic_metrics)
        
        # Prediction coverage (if confidence intervals provided)
        if confidence_lower is not None and confidence_upper is not None:
            coverage = np.mean(
                (y_true >= confidence_lower) & (y_true <= confidence_upper)
            )
            validation_metrics['coverage'] = coverage * 100  # Percentage
            
            logger.info(f"  Prediction Coverage: {coverage*100:.1f}%")
        
        # Prediction bias (systematic over/under prediction)
        bias = np.mean(y_pred - y_true)
        validation_metrics['bias'] = bias
        
        # Direction accuracy (% correct prediction direction)
        if len(y_true) > 1:
            true_direction = np.diff(y_true) > 0
            pred_direction = np.diff(y_pred) > 0
            direction_accuracy = np.mean(true_direction == pred_direction)
            validation_metrics['direction_accuracy'] = direction_accuracy * 100
        
        return validation_metrics
    
    def check_overfitting(
        self,
        train_metrics: Dict[str, float],
        val_metrics: Dict[str, float],
        threshold: float = 0.2
    ) -> Tuple[bool, str]:
        """
        Check if model is overfitting
        
        Args:
            train_metrics: Metrics on training set
            val_metrics: Metrics on validation set
            threshold: Overfitting threshold (20% by default)
        
        Returns:
            is_overfitting: bool
            message: str explanation
        """
        train_rmse = train_metrics.get('rmse', train_metrics.get('train_rmse', 0))
        val_rmse = val_metrics.get('rmse', val_metrics.get('val_rmse', 0))
        
        if train_rmse == 0:
            return False, "Cannot determine - missing train RMSE"
        
        # Calculate relative difference
        diff = (val_rmse - train_rmse) / train_rmse
        
        if diff > threshold:
            return True, f"Overfitting detected: Val RMSE is {diff*100:.1f}% higher than Train RMSE"
        else:
            return False, f"No overfitting: Val RMSE is {diff*100:.1f}% higher than Train RMSE"