# 🚀 HƯỚNG DẪN DEPLOY SERVICE TRAINING LÊN AWS (CONSOLE)

> **Điều kiện**: Service Processing đã chạy và có dữ liệu Gold

---

## 📋 Chuẩn bị

### ✅ Đã hoàn thành:
- Service Processing đã deploy và chạy
- S3 Bucket đã có dữ liệu Gold (features)
- IAM Roles đã tạo (dùng chung với Ingestion/Processing)

### 📦 Cấu trúc S3 hiện tại:
```
s3://vietnam-energy-data/
├── bronze/      (từ Ingestion)
├── silver/      (từ Processing)
└── gold/        (từ Processing)
    └── features/ ← INPUT cho Training
```

### 🎯 Sau khi deploy:
```
s3://vietnam-energy-data/
├── ...
├── models/      ← MỚI: Trained models
│   └── xgboost/
│       ├── v1.0.0/
│       │   ├── model.pkl
│       │   ├── metadata.json
│       │   └── metrics.json
│       └── latest/
└── predictions/ ← MỚI: Predictions for Dashboard
    └── latest/
        └── predictions.json
```

---

## 🗺️ ROADMAP - 6 BƯỚC

```
1. Tạo ECR Repository
2. Build & Push Docker Image
3. Tạo Task Definition (CPU/RAM cao hơn)
4. Chạy Training Task thủ công (FULL_TRAIN)
5. Tạo Weekly Schedule (Train lại mỗi tuần)
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
   vietnam-energy-training
   ```

3. **Visibility**: Private

4. **Image scan on push**: ✅ Tick

5. Click **Create repository**

### 1.3. Copy Repository URI

📝 **GHI LẠI**: `123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-training`

---

## BƯỚC 2: BUILD & PUSH DOCKER IMAGE

### 2.1. Di chuyển vào thư mục training

```powershell
cd C:\path\to\vietnam-energy-forecasting\services\training
```

### 2.2. Build Docker Image

```powershell
docker build -t vietnam-energy-training:latest .
```

⏱️ **Lưu ý**: Build lâu hơn (~5-7 phút) vì phải cài XGBoost, scikit-learn

### 2.3. Login ECR

```powershell
$AWS_ACCOUNT_ID = "123456789012"  # Thay Account ID
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com"
```

### 2.4. Tag và Push

```powershell
docker tag vietnam-energy-training:latest "$AWS_ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-training:latest"

docker push "$AWS_ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-training:latest"
```

---

## BƯỚC 3: TẠO TASK DEFINITION

### 3.1. Vào ECS Console → Task Definitions

🔗 https://ap-southeast-1.console.aws.amazon.com/ecs/v2/task-definitions?region=ap-southeast-1

### 3.2. Create New Task Definition

1. Click **Create new task definition**

2. **Task definition family**: 
   ```
   vietnam-energy-training-task
   ```

### 3.3. Infrastructure

3. **Launch type**: Fargate

4. **OS/Architecture**: Linux/X86_64

5. **CPU**: **1 vCPU** ⚠️ Training cần nhiều CPU!

6. **Memory**: **2 GB** ⚠️ Training cần nhiều RAM!

7. **Task role**: `EnergyIngestionTaskRole` (dùng chung)

8. **Task execution role**: `EnergyIngestionExecutionRole`

### 3.4. Container

9. **Container name**: 
   ```
   training-container
   ```

10. **Image URI**: Paste URI từ Bước 1.3

11. **Essential**: ✅ Yes

### 3.5. Environment Variables

12. Add các biến:

| Key | Value |
|-----|-------|
| `MODE` | `FULL_TRAIN` |
| `MODEL_TYPE` | `xgboost` |
| `S3_BUCKET` | `vietnam-energy-data-yourname` |
| `LOG_LEVEL` | `INFO` |

### 3.6. Logging

13. **Log driver**: awslogs

14. **Log group**: 
    ```
    /ecs/vietnam-energy-training
    ```

15. ✅ **Auto-configure CloudWatch Logs**

### 3.7. Create

16. Click **Create**

---

## BƯỚC 4: CHẠY TRAINING TASK (FULL_TRAIN)

> 🎯 Train model lần đầu với toàn bộ Gold data

### 4.1. Vào ECS Cluster

🔗 ECS Console → Clusters → `vietnam-energy-cluster`

### 4.2. Run Task

1. Tab **Tasks** → **Run new task**

2. **Launch type**: FARGATE

3. **Task definition**: 
   - **Family**: `vietnam-energy-training-task`
   - **Revision**: Latest

### 4.3. Network

4. **VPC**: Default VPC

5. **Subnets**: Chọn subnet

6. **Security group**: `energy-ingestion-sg` (dùng chung)

7. **Public IP**: ENABLED

### 4.4. Run

8. Click **Create**

### 4.5. Monitor

9. Click vào Task ID → Tab **Logs**

**⏱️ Thời gian**: 
- **FULL_TRAIN**: 15-30 phút (tùy số lượng data)
- Nhiều hơn Processing vì train model mất thời gian

### 4.6. Xem Logs

Bạn sẽ thấy logs như:

```
🏁 Main Training Pipeline
============================================
STEP 1: LOADING DATA
📥 Loading Gold data from S3...
  Found 3 parquet files
✅ Loaded 8760 total rows

STEP 2: SPLITTING DATA
✂️ Splitting data (time-series)...
  Train: 6132 samples
  Val: 1314 samples
  Test: 1314 samples

STEP 3: TRAINING MODEL
🌳 Training XGBoost model...
  Train samples: 6132
  Val samples: 1314
  ✅ Train RMSE: 45.23
  ✅ Val RMSE: 52.67
  ✅ Val MAPE: 3.45%

STEP 4: EVALUATION
📊 Test Metrics:
  RMSE: 51.23
  MAPE: 3.21%
  MAE: 38.45
  R2: 0.89

🔍 Top 10 Features:
  temperature: 0.2453
  hour_sin: 0.1876
  ...

STEP 5: SAVING MODEL
💾 Saving xgboost model version v1.0.1234567890...
  ✅ Saved model: models/xgboost/v1.0.1234567890/model.pkl
  ✅ Saved metadata: models/xgboost/v1.0.1234567890/metadata.json
  ✅ Saved metrics: models/xgboost/v1.0.1234567890/metrics.json
  ✅ Updated latest -> v1.0.1234567890

🎉 TRAINING COMPLETED
Model Type: xgboost
Version: v1.0.1234567890
Test RMSE: 51.23
Test MAPE: 3.21%
```

### 4.7. Verify Model trên S3

Vào S3 Console → Bucket → Check:

```
models/
└── xgboost/
    ├── v1.0.1234567890/
    │   ├── model.pkl
    │   ├── metadata.json
    │   └── metrics.json
    └── latest/
        └── model.pkl
```

---

## BƯỚC 5: TẠO WEEKLY SCHEDULE

> 🔄 Tự động retrain model mỗi tuần

### 5.1. Vào EventBridge Scheduler

🔗 https://ap-southeast-1.console.aws.amazon.com/scheduler/home?region=ap-southeast-1

### 5.2. Create Schedule

1. Click **Create schedule**

2. **Schedule name**: 
   ```
   vietnam-energy-weekly-training
   ```

3. **Description**: `Weekly model retraining every Sunday at 2 AM`

4. **Schedule group**: default

### 5.3. Schedule Pattern

5. **Occurrence**: Recurring schedule

6. **Schedule type**: Cron-based schedule

7. **Cron expression**: 
   ```
   0 19 ? * SUN *
   ```
   
   > 19:00 UTC = 02:00 AM Vietnam (Sunday)

8. **Flexible time window**: Off

9. Click **Next**

### 5.4. Target

10. **Target API**: AWS ECS

11. **ECS cluster**: `vietnam-energy-cluster`

12. **ECS task definition**: 
    - **Family**: `vietnam-energy-training-task`
    - **Revision**: Latest

13. **Launch type**: FARGATE

14. **Platform version**: LATEST

### 5.5. Network

15. **VPC**: Default VPC

16. **Subnets**: Chọn subnet

17. **Security groups**: `energy-ingestion-sg`

18. **Public IP**: ENABLED

### 5.6. Execution Role

19. **Create new role for this specific resource**

20. Click **Next** → **Next** → **Create schedule**

---

## BƯỚC 6: VERIFY HỆ THỐNG

### 6.1. Check Model Files

```powershell
# List models
aws s3 ls s3://vietnam-energy-data-yourname/models/xgboost/ --recursive

# Download metadata
aws s3 cp s3://vietnam-energy-data-yourname/models/xgboost/latest/metadata.json metadata.json
```

### 6.2. View Metadata

Mở file `metadata.json`:

```json
{
  "model_type": "xgboost",
  "version": "v1.0.1234567890",
  "trained_at": "2024-12-23T10:30:00Z",
  "training_samples": 6132,
  "validation_samples": 1314,
  "test_samples": 1314,
  "features_count": 66,
  "feature_names": ["hour", "temperature", ...],
  "hyperparameters": {
    "max_depth": 6,
    "learning_rate": 0.1,
    ...
  }
}
```

### 6.3. View Metrics

```powershell
aws s3 cp s3://vietnam-energy-data-yourname/models/xgboost/latest/metrics.json metrics.json
```

```json
{
  "train_rmse": 45.23,
  "val_rmse": 52.67,
  "val_mape": 3.45,
  "rmse": 51.23,
  "mape": 3.21,
  "mae": 38.45,
  "r2": 0.89,
  "forecast_bias": -2.34
}
```

---

## 🎉 HOÀN THÀNH!

Hệ thống giờ đã:
- ✅ Thu thập dữ liệu (Ingestion - Bronze)
- ✅ Làm sạch dữ liệu (Processing - Silver)
- ✅ Tạo features (Processing - Gold)
- ✅ Train ML model (Training - Models)
- ✅ Tự động retrain mỗi tuần

---

## 🔄 LUỒNG HOẠT ĐỘNG HOÀN CHỈNH

```
┌────────────────────────────────────────────────────────┐
│  HÀNG NGÀY (01:00 AM)                                  │
├────────────────────────────────────────────────────────┤
│  Ingestion → Bronze                                    │
│       ↓                                                 │
│  Processing → Silver + Gold                            │
│       ↓                                                 │
│  [Model latest] → Predictions (for Dashboard)         │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  HÀNG TUẦN (Sunday 02:00 AM)                           │
├────────────────────────────────────────────────────────┤
│  Training → Load Gold data                             │
│       ↓                                                 │
│  Train XGBoost model                                   │
│       ↓                                                 │
│  Evaluate & Save                                       │
│       ↓                                                 │
│  Update models/xgboost/latest/                         │
└────────────────────────────────────────────────────────┘
```

---

## 💰 CHI PHÍ

| Service | Usage | Cost/Month |
|---------|-------|-----------|
| **ECS Fargate** (Training) | 20 min/week @ 1 vCPU, 2 GB | ~$1.50 |
| **S3 Storage** (Models) | ~5 GB | ~$0.12 |
| **CloudWatch Logs** | 1 GB/month | ~$0.50 |
| **EventBridge** | 4 rules/month | Free |
| **Total (Training only)** | | **~$2-3/month** |

**Combined với tất cả services**: ~$8-12/month total

---

## 🐛 TROUBLESHOOTING

### Task failed: "ModuleNotFoundError: No module named 'xgboost'"

**Fix**: Verify `requirements.txt` có `xgboost`, rebuild image

---

### Task failed: Memory Error (OOM)

**Nguyên nhân**: Quá nhiều data hoặc RAM không đủ

**Fix**:
- Tăng memory: 2 GB → 4 GB
- Hoặc giảm data (train trên subset)

---

### Metrics quá thấp (MAPE > 20%)

**Nguyên nhân**: Model chưa tốt hoặc features chưa đủ

**Fix**:
1. Check data quality trong Gold
2. Tune hyperparameters trong `config.py`
3. Thêm features trong Processing service
4. Thử model khác (LSTM, Random Forest)

---

### Model không update

**Nguyên nhân**: Schedule không chạy hoặc task fail

**Fix**:
- Check EventBridge Schedule có **Enabled** không
- Check CloudWatch Logs để xem lỗi
- Test bằng cách run task thủ công

---

## 📞 NEXT STEPS

Sau khi Training chạy ổn:

1. ✅ **Service Dashboard** - Visualize predictions & metrics
2. ✅ **Model Monitoring** - Track model performance over time
3. ✅ **A/B Testing** - Compare different models

Bạn sẵn sàng build Dashboard không? 🎨🚀