"""
main.py
🏁 Main Training Pipeline
"""
import logging
import sys
from datetime import datetime

from config import Config
from data.loader import DataLoader
from data.splitter import DataSplitter
from models.xgboost_model import XGBoostModel
from evaluation.metrics import calculate_all_metrics
from storage.model_registry import ModelRegistry

# Setup logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Main training pipeline"""
    try:
        # Print config
        print(Config.get_summary())
        
        # Validate config
        Config.validate()
        
        # ============ STEP 1: LOAD DATA ============
        logger.info("=" * 70)
        logger.info("STEP 1: LOADING DATA")
        logger.info("=" * 70)
        
        loader = DataLoader(
            bucket_name=Config.S3_BUCKET,
            gold_prefix=Config.GOLD_PREFIX
        )
        
        df = loader.load_gold_data()

        
        logger.info(f"📊 Available columns: {list(df.columns)}")
        logger.info(f"📊 Sample columns: {df.columns[:20].tolist()}")  # In 20 columns đầu
        
        X, y = loader.prepare_train_data(
            df=df,
            target_column=Config.TARGET_COLUMN,
            exclude_features=Config.EXCLUDE_FEATURES
        )
        
        # ============ STEP 2: SPLIT DATA ============
        logger.info("=" * 70)
        logger.info("STEP 2: SPLITTING DATA")
        logger.info("=" * 70)
        
        X_train, X_val, X_test, y_train, y_val, y_test = DataSplitter.time_series_split(
            X, y,
            train_ratio=Config.TRAIN_RATIO,
            val_ratio=Config.VAL_RATIO,
            test_ratio=Config.TEST_RATIO
        )
        
        # ============ STEP 3: TRAIN MODEL ============
        logger.info("=" * 70)
        logger.info("STEP 3: TRAINING MODEL")
        logger.info("=" * 70)
        
        model = XGBoostModel(hyperparameters=Config.XGBOOST_PARAMS)
        
        train_metrics = model.train(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val
        )
        
        # ============ STEP 4: EVALUATE ============
        logger.info("=" * 70)
        logger.info("STEP 4: EVALUATION")
        logger.info("=" * 70)
        
        # Test set evaluation
        y_test_pred, _ = model.predict(X_test, return_confidence=False)
        test_metrics = calculate_all_metrics(y_test.values, y_test_pred)
        
        logger.info("📊 Test Metrics:")
        for metric, value in test_metrics.items():
            logger.info(f"  {metric.upper()}: {value:.4f}")
        
        # Feature importance
        feature_importance = model.get_top_features(n=10)
        logger.info("🔍 Top 10 Features:")
        for feat, importance in feature_importance.items():
            logger.info(f"  {feat}: {importance:.4f}")
        
        # ============ STEP 5: SAVE MODEL ============
        logger.info("=" * 70)
        logger.info("STEP 5: SAVING MODEL")
        logger.info("=" * 70)
        
        # Generate version
        version = Config.MODEL_VERSION or f"v1.0.{int(datetime.now().timestamp())}"
        
        # Save metadata
        model.save_metadata(
            version=version,
            train_size=len(X_train),
            val_size=len(X_val),
            test_size=len(X_test),
            feature_names=X_train.columns.tolist()
        )
        
        # Save to S3
        registry = ModelRegistry(
            bucket_name=Config.S3_BUCKET,
            models_prefix=Config.MODELS_PREFIX
        )
        
        model_uri = registry.save_model(
            model=model,
            model_type=Config.MODEL_TYPE,
            version=version,
            metadata=model.metadata.to_dict(),
            metrics={**train_metrics, **test_metrics}
        )
        
        logger.info(f"✅ Model saved: {model_uri}")
        
        # ============ FINAL REPORT ============
        logger.info("=" * 70)
        logger.info("🎉 TRAINING COMPLETED")
        logger.info("=" * 70)
        logger.info(f"Model Type: {Config.MODEL_TYPE}")
        logger.info(f"Version: {version}")
        logger.info(f"Test RMSE: {test_metrics['rmse']:.2f}")
        logger.info(f"Test MAPE: {test_metrics['mape']:.2f}%")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()