"""
storage/model_registry.py
💾 Model Registry - Save/Load models to/from S3
"""
import logging
import json
import pickle
import boto3
from datetime import datetime
from typing import Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

class ModelRegistry:
    """Manage model versioning và storage trên S3"""
    
    def __init__(self, bucket_name: str, models_prefix: str = "models"):
        self.bucket_name = bucket_name
        self.models_prefix = models_prefix
        self.s3_client = boto3.client('s3')

    def _make_json_safe(self, obj):
        if isinstance(obj, dict):
            return {k: self._make_json_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_safe(v) for v in obj]
        elif isinstance(obj, tuple):
            return [self._make_json_safe(v) for v in obj]
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        else:
            return obj
    
    def save_model(
        self,
        model: Any,
        model_type: str,
        version: str,
        metadata: Dict = None,
        metrics: Dict = None
    ) -> str:
        """
        Save model lên S3
        
        Args:
            model: Model object (đã train)
            model_type: xgboost, lstm, etc.
            version: v1.0.0
            metadata: Model metadata
            metrics: Evaluation metrics
        
        Returns:
            str: S3 URI của model
        """
        logger.info(f"💾 Saving {model_type} model version {version}...")
        
        # Model path
        model_path = f"{self.models_prefix}/{model_type}/{version}"

        safe_metadata = self._make_json_safe(metadata)
        safe_metrics = self._make_json_safe(metrics)

        
        # Save model pickle
        model_key = f"{model_path}/model.pkl"
        model_bytes = pickle.dumps(model)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=model_key,
            Body=model_bytes
        )
        logger.info(f"  ✅ Saved model: {model_key}")
        
        # Save metadata
        if metadata:
            metadata_key = f"{model_path}/metadata.json"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(safe_metadata, indent=2)
            )
            logger.info(f"  ✅ Saved metadata: {metadata_key}")
        
        # Save metrics
        if metrics:
            metrics_key = f"{model_path}/metrics.json"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metrics_key,
                Body=json.dumps(safe_metrics, indent=2)
            )
            logger.info(f"  ✅ Saved metrics: {metrics_key}")
        
        # Update latest symlink
        self._update_latest(model_type, version)
        
        return f"s3://{self.bucket_name}/{model_key}"
    
    def load_model(
        self,
        model_type: str,
        version: str = "latest"
    ) -> Any:
        """
        Load model từ S3
        
        Args:
            model_type: xgboost, lstm, etc.
            version: v1.0.0 hoặc "latest"
        
        Returns:
            Model object
        """
        logger.info(f"📥 Loading {model_type} model version {version}...")
        
        model_path = f"{self.models_prefix}/{model_type}/{version}"
        model_key = f"{model_path}/model.pkl"
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=model_key
            )
            model_bytes = response['Body'].read()
            model = pickle.loads(model_bytes)
            
            logger.info(f"  ✅ Loaded model from {model_key}")
            return model
            
        except Exception as e:
            logger.error(f"  ❌ Failed to load model: {e}")
            raise
    
    def _update_latest(self, model_type: str, version: str):
        """Update latest symlink"""
        # In S3, we just copy the model to "latest" folder
        src_path = f"{self.models_prefix}/{model_type}/{version}"
        dst_path = f"{self.models_prefix}/{model_type}/latest"
        
        # Copy model
        self.s3_client.copy_object(
            Bucket=self.bucket_name,
            CopySource=f"{self.bucket_name}/{src_path}/model.pkl",
            Key=f"{dst_path}/model.pkl"
        )
        logger.info(f"  ✅ Updated latest -> {version}")