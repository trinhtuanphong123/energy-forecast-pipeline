# 🚀 HƯỚNG DẪN DEPLOY SERVICE MODELS LÊN AWS (CONSOLE)

> **Phiên bản**: 2.0 - Updated Architecture với Feature Strategy & Pipeline Pattern
> 
> **Điều kiện**: Service Processing đã chạy và có dữ liệu Gold Canonical

---

## 📋 Chuẩn bị

### ✅ Đã hoàn thành:
- ✅ Service Processing đã deploy và chạy
- ✅ S3 Bucket đã có dữ liệu Gold Canonical (features + enriched data)
- ✅ IAM Roles đã tạo (dùng chung với Ingestion/Processing)

### 📦 Cấu trúc S3 hiện tại:
```
s3://vietnam-energy-data/
├── bronze/          (từ Ingestion)
├── silver/          (từ Processing)
└── gold/
    └── canonical/   ← INPUT cho Training (đã có base features)
        └── year=2024/
            └── month=01/
                └── canonical_2024_01.parquet
```

### 🎯 Sau khi deploy Models Service:
```
s3://vietnam-energy-data/
├── ...
├── models/          ← MỚI: Trained models
│   └── xgboost/
│       ├── v1.0.xxxxx/
│       │   ├── model.pkl        # Sklearn Pipeline (Scaler + XGBoost)
│       │   ├── metadata.json    # Model metadata
│       │   └── metrics.json     # Performance metrics
│       └── latest/
│           └── model.pkl
└── predictions/     ← MỚI: Predictions for Dashboard (Future)
    └── latest/
        └── predictions.json
```

---

## 🏗️ KIẾN TRÚC MỚI - ĐIỂM KHÁC BIỆT

### 🔄 So với phiên bản cũ:

| Component | Phiên bản cũ | Phiên bản mới (2.0) |
|-----------|--------------|---------------------|
| **Data Input** | Gold/features (cần tạo features) | Gold/canonical (đã có base features) |
| **Feature Engineering** | Trong model code | **Strategy Pattern** (tách riêng) |
| **Model Wrapper** | Custom BaseModel | **Sklearn Pipeline** (chuẩn hóa) |
| **Preprocessing** | Custom Preprocessor | **StandardScaler** trong Pipeline |
| **Memory Usage** | ~2 GB | ~2-4 GB (do thêm lag/rolling features) |

### 🆕 Các tính năng mới:

1. **Feature Strategy Pattern**
   - XGBoost Strategy: Tạo lag features, rolling statistics
   - Dễ dàng thêm strategies cho LSTM, Prophet

2. **Sklearn Pipeline**
   - Scaler + Feature Selector + XGBoost trong 1 pipeline
   - Dễ deploy, serialize, và reproduce

3. **Tối ưu hóa**
   - Load từ Canonical (đã clean & enrich)
   - Chỉ tạo thêm lag/rolling features
   - Faster training time

---

## 🗺️ ROADMAP - 6 BƯỚC

```
1. Tạo ECR Repository
2. Build & Push Docker Image
3. Tạo Task Definition (CPU: 1 vCPU, RAM: 3 GB)
4. Chạy Training Task thủ công (FULL_TRAIN)
5. Tạo Weekly Schedule (Retrain mỗi Chủ Nhật)
6. Verify Model & Predictions
```

---

## BƯỚC 1: TẠO ECR REPOSITORY

### 1.1. Vào ECR Console

🔗 https://ap-southeast-1.console.aws.amazon.com/ecr/repositories?region=ap-southeast-1

### 1.2. Tạo Repository

1. Click **Create repository**

2. **Repository name**: 
   ```
   vietnam-energy-models
   ```

3. **Visibility**: Private

4. **Image scan on push**: ✅ Enable

5. **Encryption**: Default (AES-256)

6. Click **Create repository**

### 1.3. Copy Repository URI

📝 **GHI LẠI URI**: 
```
123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-models
```

---

## BƯỚC 2: BUILD & PUSH DOCKER IMAGE

### 2.1. Di chuyển vào thư mục models

```powershell
cd C:\path\to\vietnam-energy-forecasting\services\models
```

### 2.2. Verify cấu trúc code

```powershell
# Kiểm tra các file quan trọng
dir src\features\strategies\xgboost.py
dir src\pipelines\wrappers\xgboost_pkg.py
dir src\training\trainer.py
```

### 2.3. Build Docker Image

```powershell
docker build -t vietnam-energy-models:latest .
```

⏱️ **Thời gian build**: ~5-8 phút (cài XGBoost, scikit-learn, pandas)

### 2.4. Login vào ECR

```powershell
$AWS_ACCOUNT_ID = "123456789012"  # ⚠️ THAY ACCOUNT ID CỦA BẠN

aws ecr get-login-password --region ap-southeast-1 | `
  docker login --username AWS --password-stdin `
  "$AWS_ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com"
```

**Expected output**: `Login Succeeded`

### 2.5. Tag Image

```powershell
docker tag vietnam-energy-models:latest `
  "$AWS_ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-models:latest"
```

### 2.6. Push Image lên ECR

```powershell
docker push `
  "$AWS_ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-models:latest"
```

⏱️ **Thời gian push**: ~3-5 phút (image size ~800 MB)

### 2.7. Verify trên ECR Console

Vào ECR → Repository `vietnam-energy-models` → Check image với tag `latest`

---

## BƯỚC 3: TẠO TASK DEFINITION

### 3.1. Vào ECS Console → Task Definitions

🔗 https://ap-southeast-1.console.aws.amazon.com/ecs/v2/task-definitions?region=ap-southeast-1

### 3.2. Create New Task Definition

1. Click **Create new task definition** (màu cam)

2. **Task definition family**: 
   ```
   vietnam-energy-models-task
   ```

3. **Description** (optional):
   ```
   ML training for energy forecasting with XGBoost
   ```

### 3.3. Infrastructure Requirements

4. **Launch type**: 
   - ✅ Select **AWS Fargate**

5. **Operating system/Architecture**: 
   - Linux/X86_64

6. **CPU**: 
   ```
   1 vCPU
   ```
   
   > 💡 XGBoost training cần CPU tốt

7. **Memory**: 
   ```
   3 GB
   ```
   
   > ⚠️ **QUAN TRỌNG**: Tăng từ 2 GB lên 3 GB
   > 
   > **Lý do**: 
   > - Load Gold Canonical data (~500 MB)
   > - Tạo lag features (×5 lags) = ~2.5 GB
   > - Tạo rolling features (×4 windows) = ~2 GB
   > - XGBoost training overhead = ~500 MB
   > - **Total**: ~5.5 GB peak, cần 3 GB minimum

8. **Task role**: 
   ```
   EnergyIngestionTaskRole
   ```
   
   (Dùng chung với Ingestion/Processing)

9. **Task execution role**: 
   ```
   EnergyIngestionExecutionRole
   ```

### 3.4. Container - 1

10. **Container name**: 
    ```
    models-container
    ```

11. **Image URI**: 
    ```
    123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-models:latest
    ```
    
    ⚠️ **PASTE URI từ Bước 1.3**

12. **Essential container**: 
    - ✅ Yes

13. **Port mappings**: 
    - Để trống (không cần expose port)

### 3.5. Environment Variables

14. Click **Add environment variable** và thêm:

| Key | Value | Mô tả |
|-----|-------|-------|
| `MODE` | `FULL_TRAIN` | Training mode |
| `MODEL_TYPE` | `xgboost` | Model type |
| `FEATURE_STRATEGY` | `xgboost` | Feature engineering strategy |
| `S3_BUCKET` | `vietnam-energy-data-yourname` | ⚠️ THAY TÊN BUCKET |
| `TARGET_COLUMN` | `total_load` | Target variable |
| `LOG_LEVEL` | `INFO` | Logging level |

**Giải thích các biến mới**:
- `FEATURE_STRATEGY`: Chọn strategy tạo features (xgboost, lstm, prophet)
- `TARGET_COLUMN`: Cột target trong Canonical data

### 3.6. Logging

15. **Use log collection**: 
    - ✅ Enable

16. **Log driver**: 
    ```
    awslogs
    ```

17. **Log group**: 
    ```
    /ecs/vietnam-energy-models
    ```

18. **Log stream prefix**: 
    ```
    ecs
    ```

19. ✅ **Auto-configure CloudWatch Logs**

### 3.7. Storage (Optional)

20. **Ephemeral storage**: 
    ```
    21 GB (default)
    ```

### 3.8. Review & Create

21. Review tất cả settings

22. Click **Create** (màu cam)

---

## BƯỚC 4: CHẠY TRAINING TASK THỦ CÔNG (FULL_TRAIN)

> 🎯 **Mục đích**: Train model lần đầu với toàn bộ Gold Canonical data

### 4.1. Vào ECS Cluster

🔗 ECS Console → Clusters → `vietnam-energy-cluster`

### 4.2. Run New Task

1. Tab **Tasks** → Click **Run new task** (màu cam)

2. **Compute options**:
   - ✅ Launch type
   - Select: **FARGATE**

3. **Platform version**: 
   ```
   LATEST
   ```

### 4.3. Deployment Configuration

4. **Application type**: Task

5. **Task definition**:
   - **Family**: `vietnam-energy-models-task`
   - **Revision**: Latest (hoặc chọn revision mới nhất)

6. **Desired tasks**: 
   ```
   1
   ```

### 4.4. Networking

7. **VPC**: 
   - Select your **Default VPC**

8. **Subnets**: 
   - Select 1 hoặc nhiều subnets (ít nhất 1)

9. **Security group**: 
   - Select `energy-ingestion-sg` (dùng chung)
   - Hoặc tạo mới với outbound rules: All traffic

10. **Public IP**: 
    - ✅ **ENABLED** (cần để download packages)

### 4.5. Run Task

11. Click **Create** (màu cam)

### 4.6. Monitor Task

12. Click vào **Task ID** vừa tạo

13. Tab **Logs** → Xem real-time logs

**⏱️ Thời gian chạy**: 

- **Load Canonical**: 1-2 phút
- **Feature Engineering**: 2-3 phút (tạo lag/rolling)
- **Train XGBoost**: 10-20 phút (tùy data size)
- **Evaluate & Save**: 1-2 phút
- **TỔNG**: ~15-30 phút

### 4.7. Xem Logs chi tiết

Bạn sẽ thấy logs như sau:

```
╔══════════════════════════════════════════════════════════╗
║         TRAINING SERVICE CONFIGURATION                   ║
╚══════════════════════════════════════════════════════════╝

Mode: FULL_TRAIN
Model Type: xgboost
Feature Strategy: xgboost
S3 Bucket: vietnam-energy-data

======================================================================
🔧 Initializing components...
🏭 Creating xgboost feature strategy...
🏭 Creating xgboost pipeline...

======================================================================
🏋️ STARTING FULL TRAINING PIPELINE
======================================================================

======================================================================
STEP 1: LOADING CANONICAL DATA
======================================================================
📥 Loading Gold Canonical data from S3...
  Found 3 parquet files
✅ Loaded 8760 total rows
  Columns: 45
  Date range: 2021-01-01 00:00:00 to 2024-12-31 23:00:00

======================================================================
STEP 2: FEATURE ENGINEERING
======================================================================
🌳 Creating XGBoost features...
  Base numeric columns: 38
  Creating lag features (periods=[1, 2, 3, 24, 168])...
    ✅ Created 190 lag features
  Creating rolling features (windows=[3, 6, 12, 24])...
    ✅ Created 304 rolling features
  Dropped 168 rows with NaN from lag/rolling
✅ Created 494 new features
  Total features: 532

======================================================================
STEP 3: PREPARING TRAIN DATA
======================================================================
🔧 Preparing training data from Canonical...
  Features: 524
  Samples: 8592
  Target: total_load (mean=1523.45, std=234.67)

======================================================================
STEP 4: SPLITTING DATA
======================================================================
✂️ Splitting data (time-series sequential)...
  Train: 6014 samples
  Val: 1289 samples
  Test: 1289 samples
  Train period: 2021-01-01 to 2023-09-15
  Val period: 2023-09-15 to 2024-03-20
  Test period: 2024-03-20 to 2024-12-31

======================================================================
STEP 5: TRAINING MODEL
======================================================================
🏋️ Training XGBoost pipeline...
  Train samples: 6014
  Val samples: 1289
🔧 Building XGBoost pipeline...
  Pipeline steps: ['scaler', 'model']
  ✅ Train RMSE: 42.34
  ✅ Val RMSE: 48.76
  ✅ Val MAPE: 3.12%

======================================================================
STEP 6: EVALUATION
======================================================================
📊 Test Metrics:
  RMSE: 47.89
  MAPE: 3.08%
  MAE: 36.23
  R2: 0.91
  FORECAST_BIAS: -1.45

🔍 Top 10 Features:
  total_load_lag_1: 0.2834
  total_load_lag_24: 0.1567
  total_load_rolling_mean_24: 0.0923
  temperature: 0.0812
  hour_sin: 0.0645
  total_load_lag_168: 0.0534
  day_of_week: 0.0423
  total_load_rolling_std_24: 0.0389
  humidity: 0.0312
  is_weekend: 0.0278

======================================================================
STEP 7: SAVING MODEL
======================================================================
💾 Saving xgboost model version v1.0.1704123456...
  ✅ Saved model: models/xgboost/v1.0.1704123456/model.pkl
  ✅ Saved metadata: models/xgboost/v1.0.1704123456/metadata.json
  ✅ Saved metrics: models/xgboost/v1.0.1704123456/metrics.json
  ✅ Updated latest -> v1.0.1704123456

======================================================================
🎉 TRAINING PIPELINE COMPLETED
======================================================================
Model: xgboost
Version: v1.0.1704123456
Test RMSE: 47.89
Test MAPE: 3.08%
Total Features: 524
Duration: 1234.5s
```

### 4.8. Kiểm tra Task Status

- **Status**: STOPPED (khi hoàn thành)
- **Exit code**: 0 (success)
- **Stopped reason**: Essential container in task exited

Nếu **Exit code ≠ 0** → Check logs để debug

---

## BƯỚC 5: VERIFY MODEL TRÊN S3

### 5.1. Vào S3 Console

🔗 https://s3.console.aws.amazon.com/s3/buckets/vietnam-energy-data

### 5.2. Navigate vào Models folder

```
Bucket: vietnam-energy-data/
└── models/
    └── xgboost/
        ├── v1.0.1704123456/
        │   ├── model.pkl         (~50 MB - Sklearn Pipeline)
        │   ├── metadata.json     (~5 KB)
        │   └── metrics.json      (~1 KB)
        └── latest/
            └── model.pkl         (copy của version mới nhất)
```

### 5.3. Download & Inspect Metadata

```powershell
# Download metadata
aws s3 cp s3://vietnam-energy-data/models/xgboost/latest/metadata.json metadata.json

# View
cat metadata.json
```

**Expected content**:

```json
{
  "model_type": "xgboost",
  "version": "v1.0.1704123456",
  "training": {
    "started_at": "2024-01-09T10:30:00Z",
    "completed_at": "2024-01-09T10:50:34Z",
    "duration_seconds": 1234.5,
    "total_samples": 8592,
    "train_samples": 6014,
    "val_samples": 1289,
    "test_samples": 1289,
    "features_count": 524,
    "feature_names": [
      "hour", "day_of_week", "month", "is_weekend",
      "temperature", "humidity", "hour_sin", "hour_cos",
      "total_load_lag_1", "total_load_lag_2", "total_load_lag_3",
      "total_load_lag_24", "total_load_lag_168",
      "total_load_rolling_mean_3", "total_load_rolling_std_3",
      ...
    ],
    "mode": "FULL_TRAIN",
    "hyperparameters": {
      "objective": "reg:squarederror",
      "max_depth": 6,
      "learning_rate": 0.1,
      "n_estimators": 100,
      "subsample": 0.8,
      "colsample_bytree": 0.8
    }
  },
  "metrics": {
    "train_rmse": 42.34,
    "val_rmse": 48.76,
    "val_mape": 3.12,
    "rmse": 47.89,
    "mape": 3.08,
    "mae": 36.23,
    "r2": 0.91,
    "forecast_bias": -1.45
  },
  "tags": {
    "feature_strategy": "xgboost",
    "auto_generated": "true"
  },
  "notes": "Training completed at 2024-01-09T10:50:34Z"
}
```

### 5.4. Check Metrics

```powershell
aws s3 cp s3://vietnam-energy-data/models/xgboost/latest/metrics.json metrics.json
cat metrics.json
```

**Metrics giải thích**:

| Metric | Giá trị mẫu | Ý nghĩa |
|--------|-------------|---------|
| `rmse` | 47.89 | Root Mean Square Error (MW) |
| `mape` | 3.08% | Mean Absolute Percentage Error |
| `mae` | 36.23 | Mean Absolute Error (MW) |
| `r2` | 0.91 | R-squared (91% variance explained) |
| `forecast_bias` | -1.45 | Xu hướng under-predict (-) hoặc over-predict (+) |

**Đánh giá**:
- ✅ **MAPE < 5%**: Rất tốt
- ✅ **R² > 0.9**: Model fit tốt
- ✅ **Forecast bias gần 0**: Không bias

---

## BƯỚC 6: TẠO WEEKLY SCHEDULE (RETRAIN)

> 🔄 Tự động retrain model mỗi tuần để cập nhật với data mới

### 6.1. Vào EventBridge Scheduler

🔗 https://ap-southeast-1.console.aws.amazon.com/scheduler/home?region=ap-southeast-1

### 6.2. Create Schedule

1. Click **Create schedule** (màu cam)

2. **Schedule name**: 
   ```
   vietnam-energy-weekly-training
   ```

3. **Description**: 
   ```
   Weekly XGBoost model retraining every Sunday at 2 AM Vietnam time
   ```

4. **Schedule group**: 
   ```
   default
   ```

### 6.3. Schedule Pattern

5. **Occurrence**: 
   - ✅ Recurring schedule

6. **Schedule type**: 
   - ✅ Cron-based schedule

7. **Cron expression**: 
   ```
   0 19 ? * SUN *
   ```
   
   **Giải thích**:
   - `0` = phút 0
   - `19` = giờ 19 UTC = 02:00 AM Vietnam (UTC+7)
   - `?` = bất kỳ ngày nào trong tháng
   - `*` = mọi tháng
   - `SUN` = Chủ Nhật
   - `*` = mọi năm

8. **Flexible time window**: 
   - ✅ Off

9. **Timezone**: 
   ```
   UTC
   ```

10. Click **Next**

### 6.4. Select Target

11. **Target API**: 
    ```
    AWS ECS
    ```

12. **Invoke**: 
    ```
    Run task
    ```

### 6.5. ECS Task Configuration

13. **Cluster ARN**: 
    - Select `vietnam-energy-cluster`

14. **Task definition family**: 
    ```
    vietnam-energy-models-task
    ```

15. **Task definition revision**: 
    - ✅ Latest

16. **Launch type**: 
    ```
    FARGATE
    ```

17. **Platform version**: 
    ```
    LATEST
    ```

### 6.6. Network Configuration

18. **VPC**: 
    - Select Default VPC

19. **Subnets**: 
    - Select 1-2 subnets

20. **Security groups**: 
    - Select `energy-ingestion-sg`

21. **Auto-assign public IP**: 
    - ✅ ENABLED

### 6.7. Task Overrides (Optional)

22. **Container overrides**: Để trống

23. **Environment variables**: Để trống (dùng từ Task Definition)

### 6.8. Execution Role

24. **Use existing role**:
    - ✅ Yes
    - Select: `AmazonEventBridgeSchedulerExecutionRole` (tạo tự động)

25. Click **Next**

### 6.9. Retry Policy & Dead-letter Queue

26. **Maximum age of event**: 
    ```
    24 hours
    ```

27. **Retry attempts**: 
    ```
    2
    ```

28. **Dead-letter queue**: 
    - ⬜ Disable (không cần)

29. Click **Next**

### 6.10. Review & Create

30. Review tất cả settings

31. Click **Create schedule** (màu cam)

### 6.11. Verify Schedule

- **State**: ENABLED
- **Next run**: Chủ Nhật tới lúc 02:00 AM Vietnam time

---

## BƯỚC 7: TẠO DAILY PREDICTION SCHEDULE (FUTURE)

> 📊 Hàng ngày chạy predictions cho Dashboard

**⚠️ Tính năng này sẽ implement sau khi có Dashboard**

### Concept:

```
Schedule: Mỗi ngày 03:00 AM (sau khi Processing xong)

Flow:
1. Load latest model từ S3
2. Load latest Canonical data
3. Create features (lag/rolling)
4. Generate predictions cho 24h tới
5. Save predictions.json vào S3
   → Dashboard sẽ đọc file này
```

---

## 🎉 HOÀN THÀNH!

### ✅ Checklist cuối cùng:

- ✅ ECR Repository: `vietnam-energy-models` created
- ✅ Docker Image pushed
- ✅ Task Definition: `vietnam-energy-models-task` created
- ✅ Task chạy thành công (Exit code = 0)
- ✅ Model saved vào S3: `models/xgboost/v1.0.xxxxx/`
- ✅ Metadata & Metrics đầy đủ
- ✅ Weekly Schedule: Retrain mỗi Chủ Nhật 02:00 AM

---

## 🔄 LUỒNG HOẠT ĐỘNG HOÀN CHỈNH

```
┌────────────────────────────────────────────────────────┐
│  HÀNG NGÀY (01:00 AM) - Data Pipeline                 │
├────────────────────────────────────────────────────────┤
│  Ingestion → Bronze                                    │
│       ↓                                                 │
│  Processing → Silver + Gold Canonical                  │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  HÀNG TUẦN (Sunday 02:00 AM) - Model Training         │
├────────────────────────────────────────────────────────┤
│  1. Load Gold Canonical data                           │
│  2. Feature Engineering (XGBoost Strategy)             │
│      ├─► Create lag features (1h, 2h, 3h, 24h, 168h)  │
│      └─► Create rolling features (3h, 6h, 12h, 24h)   │
│  3. Split Train/Val/Test (time-series)                 │
│  4. Build Pipeline (Scaler + XGBoost)                  │
│  5. Train with early stopping                          │
│  6. Evaluate on test set                               │
│  7. Save model.pkl + metadata.json                     │
│  8. Update models/xgboost/latest/                      │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  FUTURE: HÀNG NGÀY (03:00 AM) - Predictions           │
├────────────────────────────────────────────────────────┤
│  1. Load latest model                                  │
│  2. Load latest Canonical data                         │
│  3. Generate predictions (next 24h)                    │
│  4. Save predictions.json                              │
│       └─► Dashboard reads this file                    │
└────────────────────────────────────────────────────────┘
```

---

## 💰 CHI PHÍ ƯỚC TÍNH

| Service | Usage | Cost/Month |
|---------|-------|-----------|
| **ECS Fargate** (Training) | ~30 min/week @ 1 vCPU, 3 GB | ~$2.50 |
| **S3 Storage** (Models) | ~200 MB (4 versions × 50 MB) | ~$0.05 |
| **CloudWatch Logs** | ~1 GB/month | ~$0.50 |
| **EventBridge** | 4 schedules/month | Free |
| **Data Transfer** (S3 → ECS) | ~2 GB/month | ~$0.18 |
| **TOTAL (Models Service)** | | **~$3-4/month** |

**Combined toàn bộ pipeline**:
- Ingestion: ~$3/month
- Processing: ~$4/month
- Models: ~$4/month
- **TỔNG**: ~$10-12/month

---

## 🐛 TROUBLESHOOTING

### ❌ Task failed: "MemoryError" hoặc "Killed"

**Nguyên nhân**: Không đủ RAM khi tạo lag/rolling features

**Fix**:
```
Task Definition → Edit → Memory: 3 GB → 4 GB
```

Hoặc giảm số features trong `config.py`:
```python
XGBOOST_FEATURE_CONFIG = {
    'lag_periods': [1, 24, 168],  # Giảm từ 5 → 3 lags
    'rolling_windows': [12, 24],  # Giảm từ 4 → 2 windows
}
```

---

### ❌ Task failed: "Target column 'total_load' not found"

**Nguyên nhân**: Mismatch tên cột giữa Processing output và Models config

**Fix**:

1. Check tên cột trong Canonical data:
   ```powershell
   aws s3 cp s3://bucket/gold/canonical/year=2024/month=01/canonical_2024_01.parquet - | head
   ```

2. Update `config.py`:
   ```python
   TARGET_COLUMN = "electricity_demand"  # Sửa lại đúng tên
   ```

3. Update Task Definition environment variable:
   ```
   TARGET_COLUMN = electricity_demand
   ```

---

### ❌ Model performance kém (MAPE > 10%)

**Nguyên nhân**: 
- Dữ liệu chất lượng kém
- Hyperparameters chưa tối ưu
- Features chưa đủ

**Fix**:

1. **Check data quality**