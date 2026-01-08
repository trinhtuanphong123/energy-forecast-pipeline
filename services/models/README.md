# 🧠 Service Training - Vietnam Energy Forecasting

## 📋 Overview

Service Training là thành phần thứ 3 trong pipeline, chịu trách nhiệm train ML models để dự báo tiêu thụ điện.

**Input**: Dữ liệu features từ S3 Gold Layer  
**Output**: 
- Trained models (S3 Models bucket)
- Model metadata & metrics
- Predictions for Dashboard

---

## 🎯 Key Features

### ✅ Model Agnostic Architecture
- Abstract base class cho tất cả models
- Dễ dàng thêm model mới (LSTM, Prophet, Random Forest)
- Factory pattern để switch models

### ✅ Standardized Output
```python
{
  "predictions": [100.5, 105.2, ...],
  "confidence_intervals": {"lower": [...], "upper": [...]},
  "feature_importance": {"temperature": 0.25, ...},
  "metadata": {"model_type": "xgboost", "version": "v1.0.0", ...}
}
```

### ✅ Model Versioning
```
models/xgboost/
├── v1.0.0/ → model.pkl, metadata.json, metrics.json
├── v1.1.0/
└── latest/ → symlink to best version
```

### ✅ Comprehensive Evaluation
- **Metrics**: RMSE, MAPE, MAE, R², Forecast Bias
- **Cross-validation**: Time-series aware CV
- **Feature importance**: Top features analysis
- **Overfitting detection**: Train/val comparison

---

## 🏗️ Architecture

```
src/
├── main.py                  # 🏁 Entry point
├── config.py                # ⚙️ Configuration
│
├── data/                    # 📊 Data handling
│   ├── loader.py           # Load from S3 Gold
│   ├── preprocessor.py     # Feature selection, scaling
│   └── splitter.py         # Train/val/test split
│
├── models/                  # 🤖 Model implementations
│   ├── base_model.py       # Abstract base class
│   ├── xgboost_model.py    # XGBoost implementation
│   └── model_factory.py    # Factory pattern
│
├── training/                # 🏋️ Training logic
│   ├── trainer.py          # Training pipeline
│   ├── hyperparameter.py   # Hyperparameter tuning
│   └── callbacks.py        # Training callbacks
│
├── evaluation/              # 📈 Evaluation
│   ├── metrics.py          # RMSE, MAPE, MAE, R²
│   └── validator.py        # Cross-validation
│
└── storage/                 # 💾 Model storage
    ├── model_registry.py   # S3 versioning
    └── metadata.py         # Metadata management
```

---

## 🚀 Quick Start

### Local Development

```bash
cd services/training
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with S3 bucket name

# Run training
MODE=FULL_TRAIN python src/main.py
```

### Docker

```bash
docker build -t vietnam-energy-training:latest .

docker run --rm \
  -e MODE=FULL_TRAIN \
  -e MODEL_TYPE=xgboost \
  -e S3_BUCKET=vietnam-energy-data \
  -e AWS_ACCESS_KEY_ID=xxx \
  -e AWS_SECRET_ACCESS_KEY=xxx \
  vietnam-energy-training:latest
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MODE` | Training mode: `FULL_TRAIN`, `INCREMENTAL`, `PREDICT` | `FULL_TRAIN` |
| `MODEL_TYPE` | Model type: `xgboost`, `lstm`, etc. | `xgboost` |
| `S3_BUCKET` | S3 bucket name | `vietnam-energy-data` |
| `MODEL_VERSION` | Model version (auto if not set) | Auto-generated |
| `LOG_LEVEL` | Logging level | `INFO` |

### Execution Modes

#### 1. FULL_TRAIN (Weekly)
- Load toàn bộ Gold data
- Train từ đầu
- Hyperparameter tuning (optional)
- Save new model version

#### 2. INCREMENTAL (Future)
- Load existing model
- Fine-tune với data mới
- Update model

#### 3. PREDICT (Daily)
- Load latest model
- Generate predictions
- Save for Dashboard

---

## 📊 Training Pipeline

```
1. LOAD DATA
   ├─ Load Gold features from S3
   ├─ Validate schema
   └─ Prepare X, y

2. SPLIT DATA
   ├─ Train: 70%
   ├─ Validation: 15%
   └─ Test: 15%

3. TRAIN MODEL
   ├─ Initialize XGBoost
   ├─ Train với early stopping
   └─ Cross-validation (optional)

4. EVALUATE
   ├─ Calculate metrics (RMSE, MAPE, MAE, R²)
   ├─ Feature importance
   └─ Confidence intervals

5. SAVE MODEL
   ├─ Save model.pkl
   ├─ Save metadata.json
   ├─ Save metrics.json
   └─ Update latest/
```

---

## 📈 Metrics

### Regression Metrics
- **RMSE** (Root Mean Square Error): Độ lệch trung bình
- **MAPE** (Mean Absolute Percentage Error): % lệch
- **MAE** (Mean Absolute Error): Sai số tuyệt đối
- **R²** (R-squared): Độ fit của model

### Time-Series Specific
- **Forecast Bias**: Xu hướng over/under predict
- **Coverage**: % predictions trong CI
- **Direction Accuracy**: % dự đoán đúng hướng

---

## 🎛️ Hyperparameter Tuning

### Grid Search

```python
param_grid = {
    'max_depth': [3, 6, 9],
    'learning_rate': [0.01, 0.1, 0.3],
    'n_estimators': [50, 100, 200]
}

tuner = HyperparameterTuner(XGBoostModel, metric='rmse')
best_params, best_score = tuner.grid_search(
    param_grid, X_train, y_train, X_val, y_val
)
```

### Random Search

```python
param_distributions = {
    'max_depth': (3, 10),
    'learning_rate': (0.01, 0.3),
    'n_estimators': (50, 200)
}

best_params, best_score = tuner.random_search(
    param_distributions, X_train, y_train, X_val, y_val, n_trials=20
)
```

---

## 💾 Model Storage

### S3 Structure

```
models/
├── xgboost/
│   ├── v1.0.0/
│   │   ├── model.pkl          # Trained model
│   │   ├── metadata.json      # Model metadata
│   │   └── metrics.json       # Performance metrics
│   ├── v1.1.0/
│   └── latest/                # Symlink to best
└── lstm/
    └── v1.0.0/
```

### Metadata Example

```json
{
  "model_type": "xgboost",
  "version": "v1.0.1234567890",
  "trained_at": "2024-12-23T10:30:00Z",
  "training_samples": 6132,
  "features_count": 66,
  "metrics": {
    "rmse": 51.23,
    "mape": 3.21,
    "r2": 0.89
  }
}
```

---

## 🔄 Adding New Models

### Step 1: Implement Model Class

```python
# models/lstm_model.py
from .base_model import BaseModel

class LSTMModel(BaseModel):
    def __init__(self, hyperparameters=None):
        super().__init__(model_type="lstm", hyperparameters=hyperparameters)
    
    def train(self, X_train, y_train, X_val=None, y_val=None):
        # LSTM training logic
        pass
    
    def predict(self, X, return_confidence=True):
        # LSTM prediction logic
        pass
    
    def get_feature_importance(self):
        # LSTM feature importance
        pass
```

### Step 2: Register in Factory

```python
# models/__init__.py
from .lstm_model import LSTMModel

# models/model_factory.py
ModelFactory.register_model('lstm', LSTMModel)
```

### Step 3: Use New Model

```python
# config.py
MODEL_TYPE = "lstm"
```

---

## 📊 Example Training Session

```bash
$ MODE=FULL_TRAIN python src/main.py

╔══════════════════════════════════════════════════════════╗
║         TRAINING SERVICE CONFIGURATION                   ║
╚══════════════════════════════════════════════════════════╝
Mode: FULL_TRAIN
Model Type: xgboost
...

======================================================================
STEP 1: LOADING DATA
======================================================================
📥 Loading Gold data from S3...
  Found 3 parquet files
✅ Loaded 8760 total rows
  Columns: 68
  Date range: 2021-01-01 to 2024-12-20

======================================================================
STEP 2: SPLITTING DATA
======================================================================
✂️ Splitting data (time-series)...
  Train: 6132 samples
  Val: 1314 samples
  Test: 1314 samples

======================================================================
STEP 3: TRAINING MODEL
======================================================================
🌳 Training XGBoost model...
  Train samples: 6132
  Val samples: 1314
  ✅ Train RMSE: 45.23
  ✅ Val RMSE: 52.67
  ✅ Val MAPE: 3.45%

======================================================================
STEP 4: EVALUATION
======================================================================
📊 Test Metrics:
  RMSE: 51.23
  MAPE: 3.21%
  MAE: 38.45
  R2: 0.89

🔍 Top 10 Features:
  temperature: 0.2453
  hour_sin: 0.1876
  day_of_week: 0.1234
  ...

======================================================================
STEP 5: SAVING MODEL
======================================================================
💾 Saving xgboost model version v1.0.1703345678...
  ✅ Saved model: models/xgboost/v1.0.1703345678/model.pkl
  ✅ Saved metadata: models/xgboost/v1.0.1703345678/metadata.json
  ✅ Saved metrics: models/xgboost/v1.0.1703345678/metrics.json
  ✅ Updated latest -> v1.0.1703345678

======================================================================
🎉 TRAINING COMPLETED
======================================================================
Model Type: xgboost
Version: v1.0.1703345678
Test RMSE: 51.23
Test MAPE: 3.21%
Duration: 127.3s
```

---

## 🐛 Troubleshooting

### Issue: "Target column not found"

**Cause**: Mismatch giữa config và Gold data

**Fix:**
```python
# config.py
TARGET_COLUMN = "electricity_demand"  # Check tên cột trong Gold data
```

### Issue: Memory Error

**Cause**: Quá nhiều data

**Fix:**
- Tăng memory: 2 GB → 4 GB
- Load data theo chunks
- Reduce features

### Issue: Poor metrics

**Fix:**
1. Check data quality
2. Tune hyperparameters
3. Add more features
4. Try different model

---

## 📞 Next Steps

- ✅ **Deploy Training Service**
- ✅ **Monitor model performance**
- ✅ **Setup weekly retraining**
- 🎨 **Build Dashboard Service**

---

## 📄 License

MIT License