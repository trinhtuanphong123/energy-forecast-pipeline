"""
pipelines/wrappers/xgboost_pkg.py
🤖 XGBoost Model Wrapper (Sklearn Pipeline)
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, Any
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectFromModel
from xgboost import XGBRegressor


logger = logging.getLogger(__name__)

class XGBoostModelWrapper:
    """
    Wrapper cho XGBoost sử dụng sklearn Pipeline
    
    Pipeline:
    1. StandardScaler - Chuẩn hóa features
    2. SelectFromModel - Feature selection (optional)
    3. XGBRegressor - Main model
    """
    
    def __init__(self, hyperparameters: Dict[str, Any] = None):
        """
        Args:
            hyperparameters: XGBoost hyperparameters
        """
        self.hyperparameters = hyperparameters or {}
        self.pipeline = None
        self.feature_names = None
        self.is_fitted = False
        self.feature_importance_ = None
    
    def build_pipeline(self) -> Pipeline:
        """
        Build sklearn Pipeline
        
        Returns:
            Pipeline: Configured pipeline
        """
        logger.info("🔧 Building XGBoost pipeline...")
        
        steps = []
        
        # Step 1: Scaler
        steps.append(('scaler', StandardScaler()))
        
        # Step 2: Feature selector (optional)
        # Uncomment để enable feature selection
        # estimator = xgb.XGBRegressor(n_estimators=10, random_state=42)
        # steps.append(('selector', SelectFromModel(estimator, threshold='median')))
        
        # Step 3: XGBoost model
        xgb_model = XGBRegressor(**self.hyperparameters)
        steps.append(('model', xgb_model))
        
        pipeline = Pipeline(steps)
        
        logger.info(f"  Pipeline steps: {[name for name, _ in steps]}")
        
        return pipeline
    
    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame = None,
        y_val: pd.Series = None
    ) -> Dict[str, float]:
        """
        Fit pipeline on training data
        
        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features (for early stopping)
            y_val: Validation target
        
        Returns:
            Dict: Training metrics
        """
        logger.info("🏋️ Training XGBoost pipeline...")
        logger.info(f"  Train samples: {len(X_train)}")
        
        # Store feature names
        self.feature_names = X_train.columns.tolist()
        
        # Build pipeline
        self.pipeline = self.build_pipeline()
        
        # Prepare eval set for early stopping
        fit_params = {}
        if X_val is not None and y_val is not None:
            logger.info(f"  Val samples: {len(X_val)}")
            
            # Transform validation data using scaler
            X_val_scaled = self.pipeline.named_steps['scaler'].transform(X_val)
            
            fit_params['model__eval_set'] = [(X_val_scaled, y_val)]
            fit_params['model__verbose'] = False
        
        # Fit pipeline
        self.pipeline.fit(X_train, y_train, **fit_params)
        
        self.is_fitted = True
        
        # Calculate training metrics
        y_train_pred = self.pipeline.predict(X_train)
        train_rmse = np.sqrt(np.mean((y_train - y_train_pred) ** 2))
        
        metrics = {
            'train_rmse': train_rmse,
            'train_samples': len(X_train)
        }
        
        # Validation metrics
        if X_val is not None:
            y_val_pred = self.pipeline.predict(X_val)
            val_rmse = np.sqrt(np.mean((y_val - y_val_pred) ** 2))
            val_mape = np.mean(np.abs((y_val - y_val_pred) / y_val)) * 100
            
            metrics.update({
                'val_rmse': val_rmse,
                'val_mape': val_mape,
                'val_samples': len(X_val)
            })
            
            logger.info(f"  ✅ Train RMSE: {train_rmse:.2f}")
            logger.info(f"  ✅ Val RMSE: {val_rmse:.2f}")
            logger.info(f"  ✅ Val MAPE: {val_mape:.2f}%")
        
        # Extract feature importance
        self._extract_feature_importance()
        
        return metrics
    
    def predict(
        self,
        X: pd.DataFrame,
        return_confidence: bool = True
    ) -> Tuple[np.ndarray, Optional[Tuple[np.ndarray, np.ndarray]]]:
        """
        Generate predictions
        
        Args:
            X: Features
            return_confidence: Return confidence intervals
        
        Returns:
            predictions: Point predictions
            confidence: (lower, upper) if return_confidence=True
        """
        if not self.is_fitted:
            raise ValueError("Pipeline chưa được fit!")
        
        # Select features
        X_selected = X[self.feature_names]
        
        # Predict
        predictions = self.pipeline.predict(X_selected)
        
        if not return_confidence:
            return predictions, None
        
        # Calculate confidence intervals (simplified bootstrap)
        confidence_lower, confidence_upper = self._calculate_confidence_intervals(
            X_selected, predictions
        )
        
        return predictions, (confidence_lower, confidence_upper)
    
    def _calculate_confidence_intervals(
        self,
        X: pd.DataFrame,
        predictions: np.ndarray,
        n_bootstrap: int = 10,
        confidence: float = 0.95
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate prediction confidence intervals using bootstrap
        
        Args:
            X: Features
            predictions: Point predictions
            n_bootstrap: Number of bootstrap samples
            confidence: Confidence level
        
        Returns:
            Tuple: (lower_bounds, upper_bounds)
        """
        # Bootstrap predictions
        bootstrap_preds = []
        
        for _ in range(n_bootstrap):
            # Sample with replacement
            indices = np.random.choice(len(X), size=len(X), replace=True)
            X_boot = X.iloc[indices]
            
            # Predict
            pred_boot = self.pipeline.predict(X_boot)
            bootstrap_preds.append(pred_boot)
        
        bootstrap_preds = np.array(bootstrap_preds)
        
        # Calculate percentiles
        alpha = (1 - confidence) / 2
        lower_percentile = alpha * 100
        upper_percentile = (1 - alpha) * 100
        
        confidence_lower = np.percentile(bootstrap_preds, lower_percentile, axis=0)
        confidence_upper = np.percentile(bootstrap_preds, upper_percentile, axis=0)
        
        return confidence_lower, confidence_upper
    
    def _extract_feature_importance(self):
        """Extract feature importance từ XGBoost model"""
        xgb_model = self.pipeline.named_steps['model']
        
        # Get importance scores
        importance_dict = xgb_model.get_booster().get_score(importance_type='gain')
        
        # Map to feature names
        self.feature_importance_ = {}
        for i, feature_name in enumerate(self.feature_names):
            xgb_feature_name = f'f{i}'
            importance = importance_dict.get(xgb_feature_name, 0.0)
            self.feature_importance_[feature_name] = importance
        
        # Normalize
        total = sum(self.feature_importance_.values())
        if total > 0:
            self.feature_importance_ = {
                k: v / total for k, v in self.feature_importance_.items()
            }
        
        # Sort
        self.feature_importance_ = dict(
            sorted(self.feature_importance_.items(), key=lambda x: x[1], reverse=True)
        )
    
    def get_feature_importance(self, top_n: int = None) -> Dict[str, float]:
        """
        Get feature importance
        
        Args:
            top_n: Return top N features (None = all)
        
        Returns:
            Dict: Feature importance scores
        """
        if self.feature_importance_ is None:
            return {}
        
        if top_n:
            return dict(list(self.feature_importance_.items())[:top_n])
        
        return self.feature_importance_
    
    def get_pipeline(self) -> Pipeline:
        """Get sklearn pipeline"""
        return self.pipeline