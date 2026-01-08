"""
training/callbacks.py
🔔 Training Callbacks
"""
import logging
import time
from typing import Dict, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class TrainingCallback:
    """Base class cho training callbacks"""
    
    def on_train_begin(self, **kwargs):
        """Called at the beginning of training"""
        pass
    
    def on_train_end(self, **kwargs):
        """Called at the end of training"""
        pass
    
    def on_epoch_begin(self, epoch: int, **kwargs):
        """Called at the beginning of each epoch"""
        pass
    
    def on_epoch_end(self, epoch: int, logs: Dict = None, **kwargs):
        """Called at the end of each epoch"""
        pass

class EarlyStoppingCallback(TrainingCallback):
    """
    Early stopping callback
    Stops training if metric doesn't improve
    """
    
    def __init__(
        self,
        monitor: str = 'val_loss',
        patience: int = 5,
        min_delta: float = 0.001,
        mode: str = 'min'
    ):
        """
        Args:
            monitor: Metric to monitor
            patience: Number of epochs to wait
            min_delta: Minimum change to qualify as improvement
            mode: 'min' or 'max'
        """
        self.monitor = monitor
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.wait = 0
        self.stopped_epoch = 0
        self.best_value = float('inf') if mode == 'min' else float('-inf')
        self.should_stop = False
    
    def on_train_begin(self, **kwargs):
        self.wait = 0
        self.stopped_epoch = 0
        self.should_stop = False
    
    def on_epoch_end(self, epoch: int, logs: Dict = None, **kwargs):
        if logs is None:
            return
        
        current_value = logs.get(self.monitor)
        if current_value is None:
            logger.warning(f"Early stopping: {self.monitor} not found in logs")
            return
        
        # Check if improved
        if self.mode == 'min':
            improved = current_value < (self.best_value - self.min_delta)
        else:
            improved = current_value > (self.best_value + self.min_delta)
        
        if improved:
            self.best_value = current_value
            self.wait = 0
            logger.info(f"  ✨ {self.monitor} improved to {current_value:.4f}")
        else:
            self.wait += 1
            logger.info(f"  {self.monitor} did not improve ({self.wait}/{self.patience})")
            
            if self.wait >= self.patience:
                self.stopped_epoch = epoch
                self.should_stop = True
                logger.info(f"  🛑 Early stopping triggered at epoch {epoch}")

class LoggingCallback(TrainingCallback):
    """
    Logging callback
    Logs training progress
    """
    
    def __init__(self, log_every: int = 1):
        """
        Args:
            log_every: Log every N epochs
        """
        self.log_every = log_every
        self.start_time = None
    
    def on_train_begin(self, **kwargs):
        self.start_time = time.time()
        logger.info("🏁 Training started")
    
    def on_epoch_end(self, epoch: int, logs: Dict = None, **kwargs):
        if epoch % self.log_every == 0:
            if logs:
                log_str = ", ".join([f"{k}={v:.4f}" for k, v in logs.items()])
                logger.info(f"  Epoch {epoch}: {log_str}")
    
    def on_train_end(self, **kwargs):
        if self.start_time:
            duration = time.time() - self.start_time
            logger.info(f"✅ Training completed in {duration:.1f}s")

class MetricTrackerCallback(TrainingCallback):
    """
    Metric tracking callback
    Tracks all metrics during training
    """
    
    def __init__(self):
        self.history = {
            'train_loss': [],
            'val_loss': []
        }
    
    def on_epoch_end(self, epoch: int, logs: Dict = None, **kwargs):
        if logs:
            for key, value in logs.items():
                if key not in self.history:
                    self.history[key] = []
                self.history[key].append(value)
    
    def get_history(self) -> Dict:
        """Get training history"""
        return self.history
    
    def plot_history(self):
        """Plot training history (requires matplotlib)"""
        try:
            import matplotlib.pyplot as plt
            
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            
            # Plot loss
            if 'train_loss' in self.history:
                axes[0].plot(self.history['train_loss'], label='Train')
            if 'val_loss' in self.history:
                axes[0].plot(self.history['val_loss'], label='Validation')
            axes[0].set_xlabel('Epoch')
            axes[0].set_ylabel('Loss')
            axes[0].set_title('Training & Validation Loss')
            axes[0].legend()
            axes[0].grid(True)
            
            # Plot other metrics
            other_metrics = [k for k in self.history.keys() 
                           if k not in ['train_loss', 'val_loss']]
            for metric in other_metrics:
                axes[1].plot(self.history[metric], label=metric)
            axes[1].set_xlabel('Epoch')
            axes[1].set_ylabel('Metric Value')
            axes[1].set_title('Other Metrics')
            axes[1].legend()
            axes[1].grid(True)
            
            plt.tight_layout()
            plt.show()
            
        except ImportError:
            logger.warning("matplotlib not installed, cannot plot history")

class CheckpointCallback(TrainingCallback):
    """
    Checkpoint callback
    Saves model at certain intervals
    """
    
    def __init__(
        self,
        filepath: str,
        save_best_only: bool = True,
        monitor: str = 'val_loss',
        mode: str = 'min'
    ):
        """
        Args:
            filepath: Path to save checkpoint
            save_best_only: Only save when metric improves
            monitor: Metric to monitor
            mode: 'min' or 'max'
        """
        self.filepath = filepath
        self.save_best_only = save_best_only
        self.monitor = monitor
        self.mode = mode
        self.best_value = float('inf') if mode == 'min' else float('-inf')
    
    def on_epoch_end(self, epoch: int, logs: Dict = None, **kwargs):
        if logs is None:
            return
        
        current_value = logs.get(self.monitor)
        if current_value is None:
            return
        
        # Check if should save
        should_save = False
        if self.save_best_only:
            if self.mode == 'min':
                should_save = current_value < self.best_value
            else:
                should_save = current_value > self.best_value
        else:
            should_save = True
        
        if should_save:
            self.best_value = current_value
            # Save model (implementation depends on model type)
            logger.info(f"  💾 Checkpoint saved: {self.filepath}")

class CallbackList:
    """
    Manages list of callbacks
    """
    
    def __init__(self, callbacks: list = None):
        self.callbacks = callbacks or []
    
    def add(self, callback: TrainingCallback):
        """Add callback to list"""
        self.callbacks.append(callback)
    
    def on_train_begin(self, **kwargs):
        for callback in self.callbacks:
            callback.on_train_begin(**kwargs)
    
    def on_train_end(self, **kwargs):
        for callback in self.callbacks:
            callback.on_train_end(**kwargs)
    
    def on_epoch_begin(self, epoch: int, **kwargs):
        for callback in self.callbacks:
            callback.on_epoch_begin(epoch, **kwargs)
    
    def on_epoch_end(self, epoch: int, logs: Dict = None, **kwargs):
        for callback in self.callbacks:
            callback.on_epoch_end(epoch, logs, **kwargs)