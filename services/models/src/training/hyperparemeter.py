"""
training/hyperparameter.py
🎛️ Hyperparameter Tuning
"""
import logging
import numpy as np
from typing import Dict, Any, List, Tuple
from sklearn.model_selection import ParameterGrid

logger = logging.getLogger(__name__)

class HyperparameterTuner:
    """
    Hyperparameter tuning cho models
    """
    
    def __init__(self, model_class, metric: str = 'rmse', minimize: bool = True):
        """
        Args:
            model_class: Model class (e.g., XGBoostModel)
            metric: Metric to optimize
            minimize: True if lower is better
        """
        self.model_class = model_class
        self.metric = metric
        self.minimize = minimize
        self.best_params = None
        self.best_score = float('inf') if minimize else float('-inf')
        self.tuning_history = []
    
    def grid_search(
        self,
        param_grid: Dict[str, List],
        X_train,
        y_train,
        X_val,
        y_val,
        max_trials: int = None
    ) -> Tuple[Dict, float]:
        """
        Grid search hyperparameter tuning
        
        Args:
            param_grid: Dict of hyperparameter ranges
            X_train: Training features
            y_train: Training target
            X_val: Validation features
            y_val: Validation target
            max_trials: Maximum number of combinations to try
        
        Returns:
            best_params: Best hyperparameters
            best_score: Best metric score
        """
        logger.info(f"🎛️ Starting grid search hyperparameter tuning...")
        logger.info(f"  Optimizing: {self.metric}")
        
        # Generate all parameter combinations
        param_combinations = list(ParameterGrid(param_grid))
        
        if max_trials and len(param_combinations) > max_trials:
            logger.warning(f"  Limiting to {max_trials} trials (out of {len(param_combinations)})")
            # Random sample
            indices = np.random.choice(len(param_combinations), max_trials, replace=False)
            param_combinations = [param_combinations[i] for i in indices]
        
        logger.info(f"  Total trials: {len(param_combinations)}")
        
        # Try each combination
        for i, params in enumerate(param_combinations, 1):
            try:
                logger.info(f"  Trial {i}/{len(param_combinations)}: {params}")
                
                # Create and train model
                model = self.model_class(hyperparameters=params)
                model.train(X_train, y_train, X_val, y_val)
                
                # Evaluate on validation set
                y_pred, _ = model.predict(X_val, return_confidence=False)
                
                # Calculate metric
                from evaluation.metrics import calculate_all_metrics
                metrics = calculate_all_metrics(y_val.values, y_pred)
                score = metrics[self.metric]
                
                logger.info(f"    {self.metric}: {score:.4f}")
                
                # Track history
                self.tuning_history.append({
                    'params': params,
                    'score': score,
                    'metrics': metrics
                })
                
                # Update best
                if self._is_better(score, self.best_score):
                    self.best_score = score
                    self.best_params = params
                    logger.info(f"    ✨ New best! {self.metric}: {score:.4f}")
                
            except Exception as e:
                logger.error(f"    ❌ Trial {i} failed: {e}")
                continue
        
        logger.info(f"✅ Grid search completed")
        logger.info(f"  Best {self.metric}: {self.best_score:.4f}")
        logger.info(f"  Best params: {self.best_params}")
        
        return self.best_params, self.best_score
    
    def random_search(
        self,
        param_distributions: Dict[str, tuple],
        X_train,
        y_train,
        X_val,
        y_val,
        n_trials: int = 10
    ) -> Tuple[Dict, float]:
        """
        Random search hyperparameter tuning
        
        Args:
            param_distributions: Dict of (min, max) for each parameter
            X_train: Training features
            y_train: Training target
            X_val: Validation features
            y_val: Validation target
            n_trials: Number of random trials
        
        Returns:
            best_params: Best hyperparameters
            best_score: Best metric score
        """
        logger.info(f"🎲 Starting random search hyperparameter tuning...")
        logger.info(f"  Trials: {n_trials}")
        
        for trial in range(1, n_trials + 1):
            try:
                # Sample random parameters
                params = self._sample_params(param_distributions)
                
                logger.info(f"  Trial {trial}/{n_trials}: {params}")
                
                # Create and train model
                model = self.model_class(hyperparameters=params)
                model.train(X_train, y_train, X_val, y_val)
                
                # Evaluate
                y_pred, _ = model.predict(X_val, return_confidence=False)
                
                from evaluation.metrics import calculate_all_metrics
                metrics = calculate_all_metrics(y_val.values, y_pred)
                score = metrics[self.metric]
                
                logger.info(f"    {self.metric}: {score:.4f}")
                
                # Track history
                self.tuning_history.append({
                    'params': params,
                    'score': score,
                    'metrics': metrics
                })
                
                # Update best
                if self._is_better(score, self.best_score):
                    self.best_score = score
                    self.best_params = params
                    logger.info(f"    ✨ New best!")
                
            except Exception as e:
                logger.error(f"    ❌ Trial {trial} failed: {e}")
                continue
        
        logger.info(f"✅ Random search completed")
        logger.info(f"  Best {self.metric}: {self.best_score:.4f}")
        logger.info(f"  Best params: {self.best_params}")
        
        return self.best_params, self.best_score
    
    def _sample_params(self, distributions: Dict[str, tuple]) -> Dict:
        """Sample random parameters from distributions"""
        params = {}
        for param_name, (min_val, max_val) in distributions.items():
            if isinstance(min_val, int):
                # Integer parameter
                params[param_name] = np.random.randint(min_val, max_val + 1)
            else:
                # Float parameter
                params[param_name] = np.random.uniform(min_val, max_val)
        return params
    
    def _is_better(self, new_score: float, current_best: float) -> bool:
        """Check if new score is better than current best"""
        if self.minimize:
            return new_score < current_best
        else:
            return new_score > current_best
    
    def get_tuning_report(self) -> str:
        """Generate tuning report"""
        if not self.tuning_history:
            return "No tuning history"
        
        report = []
        report.append("=" * 70)
        report.append("HYPERPARAMETER TUNING REPORT")
        report.append("=" * 70)
        report.append(f"Total trials: {len(self.tuning_history)}")
        report.append(f"Metric: {self.metric}")
        report.append(f"Best score: {self.best_score:.4f}")
        report.append(f"Best params: {self.best_params}")
        report.append("")
        
        # Sort by score
        sorted_history = sorted(
            self.tuning_history,
            key=lambda x: x['score'],
            reverse=not self.minimize
        )
        
        report.append("Top 5 configurations:")
        for i, result in enumerate(sorted_history[:5], 1):
            report.append(f"{i}. {self.metric}={result['score']:.4f}")
            report.append(f"   Params: {result['params']}")
        
        return "\n".join(report)