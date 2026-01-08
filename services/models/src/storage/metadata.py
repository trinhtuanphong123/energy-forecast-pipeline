"""
storage/metadata.py
📋 Model Metadata Management
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)

@dataclass
class TrainingMetadata:
    """Metadata về quá trình training"""
    
    # Training info
    started_at: str
    completed_at: str
    duration_seconds: float
    
    # Data info
    total_samples: int
    train_samples: int
    val_samples: int
    test_samples: int
    
    # Feature info
    features_count: int
    feature_names: list
    
    # Training config
    mode: str  # FULL_TRAIN, INCREMENTAL
    hyperparameters: dict
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TrainingMetadata':
        return cls(**data)

@dataclass
class ModelMetadata:
    """Complete metadata cho trained model"""
    
    # Model identity
    model_type: str
    version: str
    
    # Training metadata
    training: TrainingMetadata
    
    # Performance metrics
    metrics: Dict[str, float]
    
    # Additional info
    tags: Dict[str, str] = field(default_factory=dict)
    notes: str = ""
    
    def to_dict(self) -> dict:
        data = asdict(self)
        # Convert training metadata
        data['training'] = self.training.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ModelMetadata':
        # Reconstruct training metadata
        training_data = data.pop('training')
        training = TrainingMetadata.from_dict(training_data)
        return cls(training=training, **data)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ModelMetadata':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

class MetadataManager:
    """
    Quản lý metadata cho models
    """
    
    def __init__(self):
        self.metadata_history = []
    
    def create_training_metadata(
        self,
        mode: str,
        start_time: datetime,
        end_time: datetime,
        total_samples: int,
        train_samples: int,
        val_samples: int,
        test_samples: int,
        features: list,
        hyperparameters: dict
    ) -> TrainingMetadata:
        """
        Tạo training metadata
        
        Args:
            mode: Training mode
            start_time: Training start time
            end_time: Training end time
            total_samples: Total data samples
            train_samples: Training samples
            val_samples: Validation samples
            test_samples: Test samples
            features: List of feature names
            hyperparameters: Model hyperparameters
        
        Returns:
            TrainingMetadata
        """
        duration = (end_time - start_time).total_seconds()
        
        metadata = TrainingMetadata(
            started_at=start_time.isoformat(),
            completed_at=end_time.isoformat(),
            duration_seconds=duration,
            total_samples=total_samples,
            train_samples=train_samples,
            val_samples=val_samples,
            test_samples=test_samples,
            features_count=len(features),
            feature_names=features,
            mode=mode,
            hyperparameters=hyperparameters
        )
        
        return metadata
    
    def create_model_metadata(
        self,
        model_type: str,
        version: str,
        training_metadata: TrainingMetadata,
        metrics: Dict[str, float],
        tags: Dict[str, str] = None,
        notes: str = ""
    ) -> ModelMetadata:
        """
        Tạo complete model metadata
        
        Args:
            model_type: Type of model
            version: Model version
            training_metadata: Training metadata
            metrics: Performance metrics
            tags: Additional tags
            notes: Notes about model
        
        Returns:
            ModelMetadata
        """
        metadata = ModelMetadata(
            model_type=model_type,
            version=version,
            training=training_metadata,
            metrics=metrics,
            tags=tags or {},
            notes=notes
        )
        
        self.metadata_history.append(metadata)
        
        return metadata
    
    def compare_versions(
        self,
        version1: ModelMetadata,
        version2: ModelMetadata,
        metric: str = 'rmse'
    ) -> Dict[str, Any]:
        """
        So sánh 2 model versions
        
        Args:
            version1: First model metadata
            version2: Second model metadata
            metric: Metric to compare
        
        Returns:
            Dict: Comparison results
        """
        v1_metric = version1.metrics.get(metric, float('inf'))
        v2_metric = version2.metrics.get(metric, float('inf'))
        
        # For RMSE/MAE/MAPE - lower is better
        if metric in ['rmse', 'mae', 'mape']:
            is_better = v2_metric < v1_metric
            improvement = ((v1_metric - v2_metric) / v1_metric) * 100
        # For R2 - higher is better
        elif metric in ['r2']:
            is_better = v2_metric > v1_metric
            improvement = ((v2_metric - v1_metric) / abs(v1_metric)) * 100
        else:
            is_better = None
            improvement = 0
        
        comparison = {
            'version1': version1.version,
            'version2': version2.version,
            'metric': metric,
            'version1_value': v1_metric,
            'version2_value': v2_metric,
            'is_version2_better': is_better,
            'improvement_percentage': improvement,
            'summary': self._generate_comparison_summary(
                version1.version,
                version2.version,
                metric,
                v1_metric,
                v2_metric,
                improvement
            )
        }
        
        return comparison
    
    def _generate_comparison_summary(
        self,
        v1: str,
        v2: str,
        metric: str,
        v1_val: float,
        v2_val: float,
        improvement: float
    ) -> str:
        """Generate human-readable comparison summary"""
        
        if improvement > 0:
            return f"{v2} is {abs(improvement):.2f}% better than {v1} on {metric}"
        elif improvement < 0:
            return f"{v2} is {abs(improvement):.2f}% worse than {v1} on {metric}"
        else:
            return f"{v2} has same {metric} as {v1}"
    
    def get_best_model(
        self,
        metric: str = 'rmse',
        minimize: bool = True
    ) -> Optional[ModelMetadata]:
        """
        Tìm model tốt nhất trong history
        
        Args:
            metric: Metric to optimize
            minimize: True if lower is better (RMSE), False if higher is better (R2)
        
        Returns:
            ModelMetadata of best model
        """
        if not self.metadata_history:
            return None
        
        best_model = None
        best_value = float('inf') if minimize else float('-inf')
        
        for metadata in self.metadata_history:
            value = metadata.metrics.get(metric)
            if value is None:
                continue
            
            if minimize:
                if value < best_value:
                    best_value = value
                    best_model = metadata
            else:
                if value > best_value:
                    best_value = value
                    best_model = metadata
        
        return best_model
    
    def export_metadata_report(self) -> str:
        """
        Export toàn bộ metadata history thành report
        
        Returns:
            str: Formatted report
        """
        if not self.metadata_history:
            return "No models in history"
        
        report = []
        report.append("=" * 70)
        report.append("MODEL METADATA REPORT")
        report.append("=" * 70)
        report.append(f"Total models: {len(self.metadata_history)}")
        report.append("")
        
        for i, metadata in enumerate(self.metadata_history, 1):
            report.append(f"Model {i}: {metadata.model_type} {metadata.version}")
            report.append(f"  Trained: {metadata.training.completed_at}")
            report.append(f"  Duration: {metadata.training.duration_seconds:.1f}s")
            report.append(f"  Samples: {metadata.training.total_samples}")
            report.append(f"  Metrics:")
            for metric, value in metadata.metrics.items():
                report.append(f"    {metric}: {value:.4f}")
            report.append("")
        
        return "\n".join(report)