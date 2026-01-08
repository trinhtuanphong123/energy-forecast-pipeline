"""
models/xgboost_model.py
🌳 XGBoost Model Implementation
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import xgboost as xgb
from sklearn.preprocessing import StandardScaler

from .base_model import BaseModel

logger = logging.getLogger(__name__)

class XGBoostModel(BaseModel):
    """
    XGBoost implementation for time-series forecasting
    """
    
    def __init__(self, hyperparameters: dict = None):
        """
        Args:
            hyperparameters: XGBoost hyperparameters
        """
        super().__init__(model_type="xgboost", hyperparameters=hyperparameters)
        self.scaler = StandardScaler()
    
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame = None,
        y_val: pd.Series = None
    ) -> Dict[str, float]:
        """
        Train XGBoost model
        
        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features
            y_val: Validation target
        
        Returns:
            Dict: Training metrics
        """
        logger.info(f"🌳 Training XGBoost model...")
        logger.info(f"  Train samples: {len(X_train)}")
        if X_val is not None:
            logger.info(f"  Val samples: {len(X_val)}")
        
        # Store feature names
        self.feature_names = X_train.columns.tolist()
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Create DMatrix for XGBoost
        dtrain = xgb.DMatrix(X_train_scaled, label=y_train)
        
        # Prepare eval set if validation data provided
        eval_set = []
        if X_val is not None and y_val is not None:
            X_val_scaled = self.scaler.transform(X_val)
            dval = xgb.DMatrix(X_val_scaled, label=y_val)
            eval_set = [(dtrain, 'train'), (dval, 'val')]
        else:
            eval_set = [(dtrain, 'train')]
        
        # Get early stopping rounds from hyperparameters
        early_stopping = self.hyperparameters.pop('early_stopping_rounds', 10)
        
        # Train model
        evals_result = {}
        self.model = xgb.train(
            params=self.hyperparameters,
            dtrain=dtrain,
            num_boost_round=self.hyperparameters.get('n_estimators', 100),
            evals=eval_set,
            early_stopping_rounds=early_stopping,
            evals_result=evals_result,
            verbose_eval=False
        )
        
        self.is_trained = True
        
        # Calculate training metrics
        train_pred = self.model.predict(dtrain)
        train_rmse = np.sqrt(np.mean((y_train - train_pred) ** 2))
        
        metrics = {
            'train_rmse': train_rmse,
            'train_samples': len(X_train)
        }
        
        # Add validation metrics if available
        if X_val is not None:
            val_pred = self.model.predict(dval)
            val_rmse = np.sqrt(np.mean((y_val - val_pred) ** 2))
            val_mape = np.mean(np.abs((y_val - val_pred) / y_val)) * 100
            
            metrics.update({
                'val_rmse': val_rmse,
                'val_mape': val_mape,
                'val_samples': len(X_val)
            })
            
            logger.info(f"  ✅ Train RMSE: {train_rmse:.2f}")
            logger.info(f"  ✅ Val RMSE: {val_rmse:.2f}")
            logger.info(f"  ✅ Val MAPE: {val_mape:.2f}%")
        
        return metrics
    
    def predict(
        self,
        X: pd.DataFrame,
        return_confidence: bool = True
    ) -> Tuple[np.ndarray, Optional[Tuple[np.ndarray, np.ndarray]]]:
        """
        Generate predictions with confidence intervals
        
        Args:
            X: Features DataFrame
            return_confidence: Return confidence intervals
        
        Returns:
            predictions: Point predictions
            confidence: (lower_bound, upper_bound) if return_confidence=True
        """
        if not self.is_trained:
            raise ValueError("Model chưa được train!")
        
        self.validate_input(X)
        
        # Select only features used in training
        X_selected = X[self.feature_names]
        
        # Scale features
        X_scaled = self.scaler.transform(X_selected)
        
        # Create DMatrix
        dmatrix = xgb.DMatrix(X_scaled)
        
        # Point predictions
        predictions = self.model.predict(dmatrix)
        
        if not return_confidence:
            return predictions, None
        
        # Calculate confidence intervals
        # Method: Bootstrap or quantile prediction
        # Simplified: Use prediction std as proxy
        
        # Get leaf predictions for uncertainty estimation
        leaf_preds = []
        for i in range(min(10, self.model.num_boosted_rounds())):
            # Sample with replacement (bootstrap)
            sample_indices = np.random.choice(
                len(X_scaled),
                size=len(X_scaled),
                replace=True
            )
            X_sample = X_scaled[sample_indices]
            dmatrix_sample = xgb.DMatrix(X_sample)
            pred_sample = self.model.predict(dmatrix_sample)
            leaf_preds.append(pred_sample)
        
        leaf_preds = np.array(leaf_preds)
        
        # Calculate confidence intervals (95%)
        confidence_lower = np.percentile(leaf_preds, 2.5, axis=0)
        confidence_upper = np.percentile(leaf_preds, 97.5, axis=0)
        
        return predictions, (confidence_lower, confidence_upper)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores
        
        Returns:
            Dict: {feature_name: importance_score}
        """
        if not self.is_trained:
            return {}
        
        # Get importance scores from XGBoost
        importance_dict = self.model.get_score(importance_type='gain')
        
        # Map feature indices to names
        feature_importance = {}
        for i, feature_name in enumerate(self.feature_names):
            # XGBoost uses 'f0', 'f1', etc. as feature names
            xgb_feature_name = f'f{i}'
            importance = importance_dict.get(xgb_feature_name, 0.0)
            feature_importance[feature_name] = importance
        
        # Normalize to sum to 1.0
        total_importance = sum(feature_importance.values())
        if total_importance > 0:
            feature_importance = {
                k: v / total_importance 
                for k, v in feature_importance.items()
            }
        
        # Sort by importance (descending)
        feature_importance = dict(
            sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )
        )
        
        return feature_importance
    
    def get_top_features(self, n: int = 10) -> Dict[str, float]:
        """
        Get top N most important features
        
        Args:
            n: Number of top features
        
        Returns:
            Dict: Top N features and their importance
        """
        all_importance = self.get_feature_importance()
        return dict(list(all_importance.items())[:n])