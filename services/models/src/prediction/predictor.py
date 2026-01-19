"""
prediction/predictor.py
🔮 Prediction Pipeline for Near Real-Time Forecasting
"""
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
logger = logging.getLogger(__name__)
class ModelPredictor:
    """
    Orchestrates prediction pipeline
    
    Flow:
    1. Load trained model from S3
    2. Load recent hourly Gold data (for features)
    3. Apply feature engineering (same strategy as training)
    4. Generate predictions for next hour
    5. Save predictions to S3
    """
    
    def __init__(self, config):
        self.config = config
        self.start_time = None
        self.end_time = None
    
    def predict(
        self,
        data_loader,
        feature_strategy,
        model_registry,
        target_datetime: Tuple[str, str]  # (date, hour)
    ) -> Dict[str, Any]:
        """
        Generate predictions for target datetime
        
        Args:
            data_loader: DataLoader instance
            feature_strategy: Feature engineering strategy
            model_registry: ModelRegistry for loading model
            target_datetime: (date, hour) to predict
        
        Returns:
            Dict: Prediction results
        """
        self.start_time = datetime.utcnow()
        
        target_date, target_hour = target_datetime
        predict_hour = int(target_hour) + 1  # Predict NEXT hour
        if predict_hour >= 24:
            predict_hour = 0
            # Adjust date to next day
            target_date_obj = datetime.strptime(target_date, "%Y-%m-%d")
            target_date = (target_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
        
        logger.info("=" * 70)
        logger.info(f"🔮 GENERATING PREDICTION FOR {target_date} {predict_hour:02d}:00")
        logger.info("=" * 70)
        
        try:
            # Step 1: Load model
            logger.info("\n" + "=" * 70)
            logger.info("STEP 1: LOADING MODEL")
            logger.info("=" * 70)
            
            model_pipeline = model_registry.load_model(
                model_type=self.config.MODEL_TYPE,
                version="latest"
            )
            logger.info(f"✅ Loaded {self.config.MODEL_TYPE} model")
            
            # Step 2: Load recent Gold data
            logger.info("\n" + "=" * 70)
            logger.info("STEP 2: LOADING HISTORICAL DATA")
            logger.info("=" * 70)
            
            # Load last N hours of Gold data (for feature engineering)
            df_historical = data_loader.load_recent_hourly_gold(
                end_date=target_date,
                end_hour=target_hour,
                hours=self.config.MIN_HISTORICAL_HOURS
            )
            
            logger.info(f"✅ Loaded {len(df_historical)} hours of historical data")
            
            # Step 3: Feature engineering
            logger.info("\n" + "=" * 70)
            logger.info("STEP 3: FEATURE ENGINEERING")
            logger.info("=" * 70)
            
            df_features = feature_strategy.create_features(df_historical)
            
            # Get the LAST row (most recent hour) for prediction
            X_predict = df_features.iloc[[-1]]  # Keep as DataFrame
            
            # Remove target and excluded features
            exclude_cols = self.config.EXCLUDE_FEATURES
            feature_cols = [c for c in X_predict.columns if c not in exclude_cols]
            X_predict = X_predict[feature_cols]
            
            logger.info(f"✅ Prepared features: {len(feature_cols)} columns")
            
            # Step 4: Generate prediction
            logger.info("\n" + "=" * 70)
            logger.info("STEP 4: GENERATING PREDICTION")
            logger.info("=" * 70)
            
            predictions, (conf_lower, conf_upper) = model_pipeline.predict(
                X_predict, return_confidence=True
            )
            
            predicted_value = predictions[0]
            conf_lower_value = conf_lower[0]
            conf_upper_value = conf_upper[0]
            
            logger.info(f"✅ Predicted: {predicted_value:.2f}")
            logger.info(f"   Confidence: [{conf_lower_value:.2f}, {conf_upper_value:.2f}]")
            
            # Step 5: Prepare output
            self.end_time = datetime.utcnow()
            
            result = {
                'prediction_for': f"{target_date}T{predict_hour:02d}:00:00",
                'predicted_value': float(predicted_value),
                'confidence_lower': float(conf_lower_value),
                'confidence_upper': float(conf_upper_value),
                'model_type': self.config.MODEL_TYPE,
                'model_version': 'latest',
                'generated_at': self.end_time.isoformat(),
                'based_on_data_until': f"{target_date}T{target_hour}:00:00",
                'feature_count': len(feature_cols),
                'historical_hours_used': len(df_historical)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"💥 Prediction failed: {e}", exc_info=True)
            raise

