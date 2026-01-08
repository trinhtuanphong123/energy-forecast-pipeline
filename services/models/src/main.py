"""
main.py
🏁 Main Entry Point cho Training Service
"""
import logging
import sys
from datetime import datetime

from config import Config
from data.loader import DataLoader
from data.splitter import DataSplitter
from features.factory import FeatureStrategyFactory
from pipelines.factory import ModelPipelineFactory
from training.trainer import ModelTrainer
from storage.model_registry import ModelRegistry
from storage.metadata import MetadataManager

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
        # ============ PRINT CONFIG ============
        print(Config.get_summary())
        Config.validate()
        
        # ============ INITIALIZE COMPONENTS ============
        logger.info("🔧 Initializing components...")
        
        # Data loader
        data_loader = DataLoader(
            bucket_name=Config.S3_BUCKET,
            canonical_prefix=Config.GOLD_CANONICAL_PREFIX
        )
        
        # Feature engineering strategy
        feature_strategy = FeatureStrategyFactory.create_strategy(
            strategy_type=Config.FEATURE_STRATEGY,
            config=Config.get_feature_config()
        )
        
        # Model pipeline
        model_pipeline = ModelPipelineFactory.create_pipeline(
            model_type=Config.MODEL_TYPE,
            hyperparameters=Config.get_model_params()
        )
        
        # Data splitter
        data_splitter = DataSplitter()
        
        # Trainer
        trainer = ModelTrainer(config=Config)
        
        # ============ EXECUTE TRAINING ============
        if Config.MODE == "FULL_TRAIN":
            
            results = trainer.train_full(
                data_loader=data_loader,
                feature_strategy=feature_strategy,
                model_pipeline=model_pipeline,
                data_splitter=data_splitter
            )
            
            # ============ SAVE MODEL ============
            logger.info("\n" + "=" * 70)
            logger.info("STEP 7: SAVING MODEL")
            logger.info("=" * 70)
            
            # Generate version
            version = Config.MODEL_VERSION or f"v1.0.{int(datetime.now().timestamp())}"
            
            # Create metadata
            metadata_manager = MetadataManager()
            
            training_metadata = metadata_manager.create_training_metadata(
                mode=Config.MODE,
                start_time=trainer.start_time,
                end_time=trainer.end_time,
                total_samples=sum([
                    results['split_info']['train_samples'],
                    results['split_info']['val_samples'],
                    results['split_info']['test_samples']
                ]),
                train_samples=results['split_info']['train_samples'],
                val_samples=results['split_info']['val_samples'],
                test_samples=results['split_info']['test_samples'],
                features=model_pipeline.feature_names,
                hyperparameters=Config.get_model_params()
            )
            
            model_metadata = metadata_manager.create_model_metadata(
                model_type=Config.MODEL_TYPE,
                version=version,
                training_metadata=training_metadata,
                metrics={**results['train_metrics'], **results['test_metrics']},
                tags={
                    'feature_strategy': Config.FEATURE_STRATEGY,
                    'auto_generated': 'true'
                },
                notes=f"Training completed at {datetime.utcnow().isoformat()}"
            )
            
            # Save to S3
            registry = ModelRegistry(
                bucket_name=Config.S3_BUCKET,
                models_prefix=Config.MODELS_PREFIX
            )
            
            model_uri = registry.save_model(
                model=model_pipeline.get_pipeline(),  # Save sklearn Pipeline
                model_type=Config.MODEL_TYPE,
                version=version,
                metadata=model_metadata.to_dict(),
                metrics={**results['train_metrics'], **results['test_metrics']}
            )
            
            logger.info(f"✅ Model saved: {model_uri}")
            
            # ============ FINAL REPORT ============
            logger.info("\n" + "=" * 70)
            logger.info("🎉 TRAINING PIPELINE COMPLETED")
            logger.info("=" * 70)
            logger.info(f"Model: {Config.MODEL_TYPE}")
            logger.info(f"Version: {version}")
            logger.info(f"Test RMSE: {results['test_metrics']['rmse']:.2f}")
            logger.info(f"Test MAPE: {results['test_metrics']['mape']:.2f}%")
            logger.info(f"Total Features: {len(model_pipeline.feature_names)}")
            logger.info(f"Duration: {results['duration_seconds']:.1f}s")
            
            sys.exit(0)
        
        elif Config.MODE == "INCREMENTAL":
            logger.error("❌ INCREMENTAL mode not yet implemented")
            sys.exit(1)
        
        elif Config.MODE == "PREDICT":
            logger.error("❌ PREDICT mode not yet implemented")
            sys.exit(1)
        
        else:
            logger.error(f"❌ Unknown MODE: {Config.MODE}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()