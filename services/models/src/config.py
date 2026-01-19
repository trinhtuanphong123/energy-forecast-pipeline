"""
config.py
⚙️ Configuration Management cho Service Training (Updated)
"""
import os
from typing import Literal, List, Dict, Any

class Config:
    """Centralized configuration for Training Service"""
    
    # ============ MODE CONFIGURATION ============
    MODE: Literal["FULL_TRAIN", "INCREMENTAL", "PREDICT"] = os.getenv(
    "MODE", "FULL_TRAIN"
    )
    # ============ PREDICTION CONFIGURATION ============
    # Path for predictions output
    PREDICTIONS_PREFIX = "predictions"
 
    # Số giờ historical data cần để tạo features (phụ thuộc vào lag/rolling)
    # Với lag_periods = [1, 2, 3, 24, 168] và rolling_windows = [3, 6, 12, 24]
    # Cần ít nhất 168 giờ (7 ngày) historical data
    MIN_HISTORICAL_HOURS = 168

    # ============ S3 CONFIGURATION ============
    S3_BUCKET = os.getenv("S3_BUCKET", "vietnam-energy-data")
    
    # Data paths - ĐỌC TỪ GOLD CANONICAL (đã có features)
    GOLD_CANONICAL_PREFIX = "gold/canonical"  # Output từ Processing service
    MODELS_PREFIX = "models"
    # PREDICTIONS_PREFIX = "predictions"
    
    # ============ MODEL CONFIGURATION ============
    MODEL_TYPE = os.getenv("MODEL_TYPE", "xgboost")
    MODEL_VERSION = os.getenv("MODEL_VERSION", None)
    
    # ============ TARGET VARIABLE ============
    # Target column trong Gold Canonical
    TARGET_COLUMN = "electricity_demand" # Hoặc "total_load"
    
    # Columns to exclude (metadata, không phải features)
    EXCLUDE_FEATURES = [
        'datetime',           # Timestamp
        'query_date',         # Processing metadata
        'source',             # Data source
        'processed_at',       # Processing timestamp
        'signal',             # Signal column
        TARGET_COLUMN         # Target không phải feature
    ]
    
    # ============ FEATURE ENGINEERING STRATEGY ============
    # Strategy: "xgboost", "lstm", "prophet"
    FEATURE_STRATEGY = os.getenv("FEATURE_STRATEGY", "xgboost")
    
    # XGBoost-specific features (nếu cần thêm features từ Canonical)
    XGBOOST_FEATURE_CONFIG = {
        'create_lags': True,
        'lag_periods': [1, 2, 3, 24, 168],  # 1h, 2h, 3h, 1day, 1week
        'create_rolling': True,
        'rolling_windows': [3, 6, 12, 24],  # 3h, 6h, 12h, 24h
        'create_interactions': False  # Tương tác giữa features
    }
    
    # ============ DATA SPLIT ============
    TRAIN_RATIO = 0.7
    VAL_RATIO = 0.15
    TEST_RATIO = 0.15
    RANDOM_STATE = 42
    
    # ============ MODEL PIPELINE CONFIGURATION ============
    # Sklearn Pipeline steps
    PIPELINE_STEPS = [
        'scaler',      # StandardScaler
        'selector',    # Feature selection (optional)
        'model'        # XGBRegressor
    ]
    
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
    
    # ============ EVALUATION ============
    CV_FOLDS = 5
    METRICS = ['rmse', 'mape', 'mae', 'r2', 'forecast_bias']
    CONFIDENCE_LEVEL = 0.95
    
    # ============ PREDICTION ============
    FORECAST_HORIZON = 24  # hours
    PREDICTION_FREQUENCY = 'H'
    
    # ============ MODEL REGISTRY ============
    VERSION_FORMAT = "v{major}.{minor}.{patch}"
    KEEP_VERSIONS = 5
    AUTO_PROMOTE = True
    PROMOTION_METRIC = 'rmse'
    
    # ============ LOGGING ============
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # ============ PERFORMANCE ============
    MAX_MEMORY_GB = 4
    BATCH_SIZE = 10000

    
    @staticmethod
    def get_feature_config() -> Dict[str, Any]:
        """Get feature engineering config cho strategy hiện tại"""
        if Config.FEATURE_STRATEGY == "xgboost":
            return Config.XGBOOST_FEATURE_CONFIG
        else:
            return {}
    
    @staticmethod
    def get_model_params() -> Dict[str, Any]:
        """Get hyperparameters cho model type"""
        if Config.MODEL_TYPE == "xgboost":
            return Config.XGBOOST_PARAMS
        else:
            raise ValueError(f"Unknown model type: {Config.MODEL_TYPE}")
    
    @staticmethod
    def get_model_path(version: str = None) -> str:
        """Get S3 path for model"""
        if version is None:
            version = "latest"
        return f"{Config.MODELS_PREFIX}/{Config.MODEL_TYPE}/{version}"
    
    @staticmethod
    def validate():
        """Validate configuration"""
        errors = []
        
        if not Config.S3_BUCKET:
            errors.append("❌ S3_BUCKET không được set")
        
        valid_modes = ["FULL_TRAIN", "INCREMENTAL", "PREDICT"]
        if Config.MODE not in valid_modes:
            errors.append(f"❌ MODE không hợp lệ: {Config.MODE}")
        
        total_ratio = Config.TRAIN_RATIO + Config.VAL_RATIO + Config.TEST_RATIO
        if abs(total_ratio - 1.0) > 0.01:
            errors.append(f"❌ Split ratios phải = 1.0 (hiện tại: {total_ratio})")
        
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
Feature Strategy: {Config.FEATURE_STRATEGY}
S3 Bucket: {Config.S3_BUCKET}

Data:
  • Gold Canonical: {Config.GOLD_CANONICAL_PREFIX}
  • Target: {Config.TARGET_COLUMN}
  • Split: {Config.TRAIN_RATIO}/{Config.VAL_RATIO}/{Config.TEST_RATIO}

Feature Engineering:
  • Lags: {Config.XGBOOST_FEATURE_CONFIG.get('lag_periods', [])}
  • Rolling: {Config.XGBOOST_FEATURE_CONFIG.get('rolling_windows', [])}

Model Pipeline:
  • Steps: {' → '.join(Config.PIPELINE_STEPS)}
  • Max Depth: {Config.XGBOOST_PARAMS.get('max_depth')}
  • Learning Rate: {Config.XGBOOST_PARAMS.get('learning_rate')}
  • N Estimators: {Config.XGBOOST_PARAMS.get('n_estimators')}

Evaluation:
  • CV Folds: {Config.CV_FOLDS}
  • Metrics: {', '.join(Config.METRICS)}
        """