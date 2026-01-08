"""
config.py
⚙️ Configuration Management cho Service Training
"""
import os
from typing import Literal, List, Dict, Any

class Config:
    """Centralized configuration for Training Service"""
    
    # ============ MODE CONFIGURATION ============
    # FULL_TRAIN: Train từ đầu với toàn bộ data
    # INCREMENTAL: Retrain với data mới
    # PREDICT: Chỉ generate predictions
    MODE: Literal["FULL_TRAIN", "INCREMENTAL", "PREDICT"] = os.getenv(
        "MODE", "FULL_TRAIN"
    )
    
    # ============ S3 CONFIGURATION ============
    S3_BUCKET = os.getenv("S3_BUCKET", "vietnam-energy-data")
    
    # Data paths
    GOLD_PREFIX = "gold/features"
    MODELS_PREFIX = "models"
    PREDICTIONS_PREFIX = "predictions"
    
    # ============ MODEL CONFIGURATION ============
    # Model type: xgboost, lstm, random_forest
    MODEL_TYPE = os.getenv("MODEL_TYPE", "xgboost")
    
    # Model version (auto-increment nếu không set)
    MODEL_VERSION = os.getenv("MODEL_VERSION", None)
    
    # ============ TARGET VARIABLE ============
    # Tên cột target trong Gold data
    # TODO: Cần confirm với Processing service output
    TARGET_COLUMN = "electricity_demand"  # Hoặc "total_load", "carbon_intensity"
    
    # Features to exclude từ training (không phải predictors)
    EXCLUDE_FEATURES = [
        'datetime',
        'query_date',
        'source',
        'processed_at',
        'signal',
        TARGET_COLUMN  # Target không phải feature
    ]
    
    # ============ DATA SPLIT ============
    TRAIN_RATIO = 0.7
    VAL_RATIO = 0.15
    TEST_RATIO = 0.15
    RANDOM_STATE = 42
    
    # ============ XGBOOST HYPERPARAMETERS ============
    XGBOOST_PARAMS = {
        'objective': 'reg:squarederror',
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 1,
        'gamma': 0,
        'reg_alpha': 0,
        'reg_lambda': 1,
        'random_state': RANDOM_STATE,
        'n_jobs': -1,
        'verbosity': 1
    }
    
    # Early stopping
    EARLY_STOPPING_ROUNDS = 10
    
    # ============ LSTM HYPERPARAMETERS (Future) ============
    LSTM_PARAMS = {
        'hidden_size': 64,
        'num_layers': 2,
        'dropout': 0.2,
        'learning_rate': 0.001,
        'epochs': 50,
        'batch_size': 32
    }
    
    # ============ FEATURE ENGINEERING ============
    # Feature selection
    FEATURE_IMPORTANCE_THRESHOLD = 0.01  # Drop features < 1% importance
    MAX_FEATURES = 50  # Limit số features
    
    # Feature scaling
    SCALING_METHOD = "standard"  # standard, minmax, robust
    
    # ============ EVALUATION ============
    # Cross-validation
    CV_FOLDS = 5
    
    # Metrics to track
    METRICS = [
        'rmse',
        'mape', 
        'mae',
        'r2',
        'forecast_bias'
    ]
    
    # Confidence interval
    CONFIDENCE_LEVEL = 0.95  # 95% confidence interval
    
    # ============ PREDICTION ============
    # Forecast horizon (hours)
    FORECAST_HORIZON = 24  # Dự báo 24 giờ tới
    
    # Prediction frequency
    PREDICTION_FREQUENCY = 'H'  # Hourly
    
    # ============ MODEL REGISTRY ============
    # Model versioning format
    VERSION_FORMAT = "v{major}.{minor}.{patch}"
    
    # Keep last N versions
    KEEP_VERSIONS = 5
    
    # Auto-promote to latest if metrics improve
    AUTO_PROMOTE = True
    PROMOTION_METRIC = 'rmse'  # Metric to compare
    
    # ============ LOGGING ============
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # ============ PERFORMANCE ============
    # Memory limit for data loading (GB)
    MAX_MEMORY_GB = 4
    
    # Batch size for large datasets
    BATCH_SIZE = 10000
    
    @staticmethod
    def get_model_params() -> Dict[str, Any]:
        """Get hyperparameters cho model type hiện tại"""
        if Config.MODEL_TYPE == "xgboost":
            return Config.XGBOOST_PARAMS
        elif Config.MODEL_TYPE == "lstm":
            return Config.LSTM_PARAMS
        else:
            raise ValueError(f"Unknown model type: {Config.MODEL_TYPE}")
    
    @staticmethod
    def get_model_path(version: str = None) -> str:
        """
        Get S3 path for model
        
        Args:
            version: Model version (e.g., "v1.0.0")
                    If None, returns "latest"
        
        Returns:
            str: S3 path
        """
        if version is None:
            version = "latest"
        
        return f"{Config.MODELS_PREFIX}/{Config.MODEL_TYPE}/{version}"
    
    @staticmethod
    def validate():
        """Validate configuration"""
        errors = []
        
        # Check S3 bucket
        if not Config.S3_BUCKET:
            errors.append("❌ S3_BUCKET không được set")
        
        # Check mode
        valid_modes = ["FULL_TRAIN", "INCREMENTAL", "PREDICT"]
        if Config.MODE not in valid_modes:
            errors.append(f"❌ MODE không hợp lệ: {Config.MODE}")
        
        # Check model type
        valid_models = ["xgboost", "lstm", "random_forest"]
        if Config.MODEL_TYPE not in valid_models:
            errors.append(f"❌ MODEL_TYPE không hợp lệ: {Config.MODEL_TYPE}")
        
        # Check split ratios
        total_ratio = Config.TRAIN_RATIO + Config.VAL_RATIO + Config.TEST_RATIO
        if abs(total_ratio - 1.0) > 0.01:
            errors.append(f"❌ Data split ratios phải tổng = 1.0 (hiện tại: {total_ratio})")
        
        if errors:
            raise ValueError("\n".join(errors))
        
        return True
    
    @staticmethod
    def get_summary() -> str:
        """Print configuration summary"""
        return f"""
╔══════════════════════════════════════════════════════════╗
║         TRAINING SERVICE CONFIGURATION                   ║
╚══════════════════════════════════════════════════════════╝

Mode: {Config.MODE}
Model Type: {Config.MODEL_TYPE}
S3 Bucket: {Config.S3_BUCKET}

Data:
  • Gold Path: {Config.GOLD_PREFIX}
  • Target Column: {Config.TARGET_COLUMN}
  • Train/Val/Test: {Config.TRAIN_RATIO}/{Config.VAL_RATIO}/{Config.TEST_RATIO}

Model:
  • Max Depth: {Config.XGBOOST_PARAMS.get('max_depth', 'N/A')}
  • Learning Rate: {Config.XGBOOST_PARAMS.get('learning_rate', 'N/A')}
  • N Estimators: {Config.XGBOOST_PARAMS.get('n_estimators', 'N/A')}
  • Early Stopping: {Config.EARLY_STOPPING_ROUNDS} rounds

Evaluation:
  • CV Folds: {Config.CV_FOLDS}
  • Metrics: {', '.join(Config.METRICS)}
  • Confidence Level: {Config.CONFIDENCE_LEVEL}

Prediction:
  • Forecast Horizon: {Config.FORECAST_HORIZON} hours
  • Frequency: {Config.PREDICTION_FREQUENCY}

Model Registry:
  • Models Path: {Config.MODELS_PREFIX}/{Config.MODEL_TYPE}/
  • Keep Versions: {Config.KEEP_VERSIONS}
  • Auto Promote: {Config.AUTO_PROMOTE}
        """