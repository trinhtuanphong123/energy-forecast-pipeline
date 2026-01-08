"""
training/trainer.py
🏋️ Main Training Orchestrator (Conductor)
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

class ModelTrainer:
    """
    Orchestrates toàn bộ training pipeline
    
    Flow:
    1. Load canonical data
    2. Apply feature engineering strategy
    3. Split data
    4. Train model pipeline
    5. Evaluate
    6. Save model & metadata
    """
    
    def __init__(self, config):
        """
        Args:
            config: Config object (from config.py)
        """
        self.config = config
        self.start_time = None
        self.end_time = None
        self.training_history = {}
    
    def train_full(
        self,
        data_loader,
        feature_strategy,
        model_pipeline,
        data_splitter
    ) -> Dict[str, Any]:
        """
        Full training pipeline
        
        Args:
            data_loader: DataLoader instance
            feature_strategy: Feature engineering strategy
            model_pipeline: Model pipeline wrapper
            data_splitter: DataSplitter instance
        
        Returns:
            Dict: Training results
        """
        logger.info("=" * 70)
        logger.info("🏋️ STARTING FULL TRAINING PIPELINE")
        logger.info("=" * 70)
        
        self.start_time = datetime.utcnow()
        
        try:
            # ============ STEP 1: LOAD DATA ============
            logger.info("\n" + "=" * 70)
            logger.info("STEP 1: LOADING CANONICAL DATA")
            logger.info("=" * 70)
            
            df_canonical = data_loader.load_canonical_data()
            
            # ============ STEP 2: FEATURE ENGINEERING ============
            logger.info("\n" + "=" * 70)
            logger.info("STEP 2: FEATURE ENGINEERING")
            logger.info("=" * 70)
            
            df_features = feature_strategy.create_features(df_canonical)
            
            # ============ STEP 3: PREPARE TRAIN DATA ============
            logger.info("\n" + "=" * 70)
            logger.info("STEP 3: PREPARING TRAIN DATA")
            logger.info("=" * 70)
            
            X, y, timestamps = data_loader.prepare_train_data(
                df=df_features,
                target_column=self.config.TARGET_COLUMN,
                exclude_features=self.config.EXCLUDE_FEATURES
            )
            
            # ============ STEP 4: SPLIT DATA ============
            logger.info("\n" + "=" * 70)
            logger.info("STEP 4: SPLITTING DATA")
            logger.info("=" * 70)
            
            (X_train, X_val, X_test, 
             y_train, y_val, y_test,
             ts_train, ts_val, ts_test) = data_splitter.time_series_split(
                X=X,
                y=y,
                timestamps=timestamps,
                train_ratio=self.config.TRAIN_RATIO,
                val_ratio=self.config.VAL_RATIO,
                test_ratio=self.config.TEST_RATIO
            )
            
            # ============ STEP 5: TRAIN MODEL ============
            logger.info("\n" + "=" * 70)
            logger.info("STEP 5: TRAINING MODEL")
            logger.info("=" * 70)
            
            train_metrics = model_pipeline.fit(
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val
            )
            
            # ============ STEP 6: EVALUATE ============
            logger.info("\n" + "=" * 70)
            logger.info("STEP 6: EVALUATION")
            logger.info("=" * 70)
            
            from evaluation.metrics import calculate_all_metrics
            
            # Test set evaluation
            y_test_pred, (conf_lower, conf_upper) = model_pipeline.predict(
                X_test, return_confidence=True
            )
            
            test_metrics = calculate_all_metrics(y_test.values, y_test_pred)
            
            logger.info("📊 Test Metrics:")
            for metric, value in test_metrics.items():
                logger.info(f"  {metric.upper()}: {value:.4f}")
            
            # Feature importance
            feature_importance = model_pipeline.get_feature_importance(top_n=10)
            logger.info("\n🔍 Top 10 Features:")
            for feat, imp in feature_importance.items():
                logger.info(f"  {feat}: {imp:.4f}")
            
            # ============ END ============
            self.end_time = datetime.utcnow()
            duration = (self.end_time - self.start_time).total_seconds()
            
            # Compile results
            results = {
                'train_metrics': train_metrics,
                'test_metrics': test_metrics,
                'feature_importance': feature_importance,
                'feature_info': feature_strategy.get_feature_info(),
                'split_info': {
                    'train_samples': len(X_train),
                    'val_samples': len(X_val),
                    'test_samples': len(X_test)
                },
                'duration_seconds': duration,
                'model_pipeline': model_pipeline,
                'timestamps': {
                    'train': ts_train,
                    'val': ts_val,
                    'test': ts_test
                }
            }
            
            logger.info("\n" + "=" * 70)
            logger.info("🎉 TRAINING COMPLETED SUCCESSFULLY")
            logger.info("=" * 70)
            logger.info(f"Duration: {duration:.1f}s")
            logger.info(f"Test RMSE: {test_metrics['rmse']:.2f}")
            logger.info(f"Test MAPE: {test_metrics['mape']:.2f}%")
            
            self.training_history = results
            
            return results
            
        except Exception as e:
            logger.error(f"💥 Training failed: {e}", exc_info=True)
            raise
    
    def get_training_summary(self) -> str:
        """Get training summary"""
        if not self.training_history:
            return "No training history"
        
        summary = []
        summary.append("=" * 70)
        summary.append("TRAINING SUMMARY")
        summary.append("=" * 70)
        
        if self.start_time:
            summary.append(f"Started: {self.start_time.isoformat()}")
        if self.end_time:
            summary.append(f"Completed: {self.end_time.isoformat()}")
            summary.append(f"Duration: {self.training_history['duration_seconds']:.1f}s")
        
        summary.append("\nTest Metrics:")
        for k, v in self.training_history['test_metrics'].items():
            summary.append(f"  {k}: {v:.4f}")
        
        return "\n".join(summary)