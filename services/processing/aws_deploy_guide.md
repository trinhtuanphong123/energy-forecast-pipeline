# 🚀 HƯỚNG DẪN DEPLOY SERVICE PROCESSING LÊN AWS (CONSOLE)

> **Lưu ý**: Service Processing phụ thuộc vào Service Ingestion. Đảm bảo Service Ingestion đã chạy và có dữ liệu Bronze trước khi deploy service này.

---

## 📋 Điều kiện tiên quyết

### ✅ Đã hoàn thành:
- Service Ingestion đã deploy và chạy
- S3 Bucket đã có dữ liệu Bronze (từ Service Ingestion)
- IAM User cho GitHub Actions (nếu dùng CI/CD)
- Docker Desktop đã cài trên máy

### 📦 Cấu trúc S3 hiện tại:
```
s3://vietnam-energy-data/
└── bronze/
    ├── weather/year=2024/month=12/day=*/data.json
    └── electricity/*/year=2024/month=12/day=*/data.json
```

### 🎯 Sau khi deploy, sẽ có thêm:
```
s3://vietnam-energy-data/
├── bronze/      (đã có)
├── silver/      (← MỚI: cleaned data)
│   ├── weather/
│   └── electricity/
└── gold/        (← MỚI: features for ML)
    └── features/
```

---

## 🗺️ ROADMAP - 7 BƯỚC

```
1. Tạo ECR Repository (cho Processing service)
2. Build & Push Docker Image
3. Tạo/Cập nhật IAM Roles (thêm quyền nếu cần)
4. Tạo Task Definition
5. Tạo S3 Event Trigger (tự động chạy khi có data mới)
6. Chạy Backfill thủ công (1 lần)
7. Test tự động trigger
```

---

## BƯỚC 1: TẠO ECR REPOSITORY

### 1.1. Vào ECR Console

🔗 https://ap-southeast-1.console.aws.amazon.com/ecr/repositories?region=ap-southeast-1

### 1.2. Tạo Repository

1. Click **Create repository**

2. **Repository name**: 
   ```
   vietnam-energy-processing
   ```

3. **Visibility**: Private

4. **Image scan on push**: ✅ Tick

5. Click **Create repository**

### 1.3. Lưu Repository URI

Copy **URI** (dạng: `123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-processing`)

📝 **GHI LẠI**: Repository URI

---

## BƯỚC 2: BUILD & PUSH DOCKER IMAGE

> ⚠️ Cần PowerShell

### 2.1. Mở PowerShell và di chuyển vào thư mục

```powershell
cd C:\path\to\vietnam-energy-forecasting\services\processing
```

### 2.2. Build Docker Image

```powershell
docker build -t vietnam-energy-processing:latest .
```

### 2.3. Login ECR

```powershell
$AWS_ACCOUNT_ID = "123456789012"  # Thay bằng Account ID của bạn

aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com"
```

### 2.4. Tag và Push

```powershell
docker tag vietnam-energy-processing:latest "$AWS_ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-processing:latest"

docker push "$AWS_ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-processing:latest"
```

---

## BƯỚC 3: KIỂM TRA IAM ROLES

Service Processing cần **CÙNG IAM Roles** như Service Ingestion.

### Kiểm tra Roles hiện có:

🔗 https://console.aws.amazon.com/iam/home#/roles

Tìm 2 roles:
- ✅ `EnergyIngestionTaskRole` (Task Role)
- ✅ `EnergyIngestionExecutionRole` (Execution Role)

### Nếu chưa có, tạo mới theo hướng dẫn Service Ingestion

> 💡 Processing service sử dụng chung IAM Roles với Ingestion service vì cùng access S3 bucket.

---

## BƯỚC 4: TẠO TASK DEFINITION

### 4.1. Vào ECS Console → Task Definitions

🔗 https://ap-southeast-1.console.aws.amazon.com/ecs/v2/task-definitions?region=ap-southeast-1

### 4.2. Create New Task Definition

1. Click **Create new task definition**

2. **Task definition family**: 
   ```
   vietnam-energy-processing-task
   ```

### 4.3. Infrastructure

3. **Launch type**: Fargate

4. **OS/Architecture**: Linux/X86_64

5. **CPU**: **0.5 vCPU** (Processing cần nhiều CPU hơn Ingestion)

6. **Memory**: **1 GB** (Pandas cần nhiều RAM)

7. **Task role**: `EnergyIngestionTaskRole`

8. **Task execution role**: `EnergyIngestionExecutionRole`

### 4.4. Container

9. **Container name**: 
   ```
   processing-container
   ```

10. **Image URI**: Paste URI từ Bước 1.3
    ```
    123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-processing:latest
    ```

11. **Essential**: ✅ Yes

### 4.5. Environment Variables

12. Add các biến:

| Key | Value |
|-----|-------|
| `MODE` | `DAILY` |
| `S3_BUCKET` | `vietnam-energy-data-yourname` |
| `LOG_LEVEL` | `INFO` |

### 4.6. Logging

13. **Log driver**: awslogs

14. **Log group**: 
    ```
    /ecs/vietnam-energy-processing
    ```

15. ✅ **Auto-configure CloudWatch Logs**

### 4.7. Create

16. Click **Create**

---

## BƯỚC 5: TẠO S3 EVENT TRIGGER

> 🎯 Mục đích: Tự động chạy Processing task khi Ingestion task ghi data mới vào S3 Bronze

### 5.1. Tạo EventBridge Rule

🔗 https://ap-southeast-1.console.aws.amazon.com/events/home?region=ap-southeast-1#/rules

1. Click **Create rule**

2. **Name**: 
   ```
   trigger-processing-on-bronze-data
   ```

3. **Description**: `Trigger processing when new Bronze data arrives`

4. **Event bus**: default

5. **Rule type**: Rule with an event pattern

6. Click **Next**

### 5.2. Event Pattern

7. **Event source**: AWS services

8. **AWS service**: S3

9. **Event type**: Amazon S3 Event Notification

10. **Event pattern** - Click **Edit pattern** (JSON):

```json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "detail": {
    "bucket": {
      "name": ["vietnam-energy-data-yourname"]
    },
    "object": {
      "key": [{
        "prefix": "bronze/weather/"
      }]
    }
  }
}
```

> ⚠️ Thay `vietnam-energy-data-yourname` bằng tên bucket thật!

11. Click **Next**

### 5.3. Target

12. **Target types**: AWS service

13. **Select a target**: ECS task

14. **Cluster**: `vietnam-energy-cluster`

15. **Task definition**: 
    - **Family**: `vietnam-energy-processing-task`
    - **Revision**: Latest

16. **Launch type**: FARGATE

17. **Platform version**: LATEST

### 5.4. Network Configuration

18. **VPC**: Chọn VPC mặc định

19. **Subnets**: Chọn subnet (same as Ingestion)

20. **Security groups**: Chọn `energy-ingestion-sg`

21. **Public IP**: ENABLED

### 5.5. Execution Role

22. **Create a new role for this specific resource**

23. Click **Next** → **Next** → **Create rule**

### ⚠️ LƯU Ý VỀ S3 EVENT NOTIFICATIONS

Để EventBridge nhận được S3 events, cần enable S3 Event Notifications:

#### Enable S3 to EventBridge:

1. Vào S3 Console → Click vào bucket `vietnam-energy-data-yourname`

2. Tab **Properties** → Scroll xuống **Amazon EventBridge**

3. Click **Edit**

4. ✅ Tick **Send notifications to Amazon EventBridge for all events in this bucket**

5. Click **Save changes**

---

## BƯỚC 6: CHẠY BACKFILL (1 LẦN)

> Xử lý tất cả dữ liệu Bronze đã có từ Service Ingestion

### 6.1. Vào ECS Cluster

🔗 ECS Console → Clusters → `vietnam-energy-cluster`

### 6.2. Run Task

1. Tab **Tasks** → **Run new task**

2. **Launch type**: FARGATE

3. **Task definition**: 
   - **Family**: `vietnam-energy-processing-task`
   - **Revision**: Latest

### 6.3. Network

4. **VPC**: Default VPC

5. **Subnets**: Chọn subnet

6. **Security group**: `energy-ingestion-sg`

7. **Public IP**: ENABLED

### 6.4. Container Override (QUAN TRỌNG!)

8. Expand **Container overrides**

9. Click `processing-container`

10. Trong **Environment variable overrides**, sửa `MODE`:
    ```
    MODE = BACKFILL
    ```

11. Click **Update**

### 6.5. Run

12. Click **Create**

### 6.6. Monitor

13. Click vào Task ID → Tab **Logs**

14. Xem logs real-time

**⏱️ Thời gian**: 
- BACKFILL: 20-40 phút (tùy số lượng ngày)
- Xử lý nhanh hơn Ingestion vì không gọi API

### 6.7. Kiểm tra kết quả

Vào S3 Console → Bucket → Kiểm tra:

```
silver/
├── weather/year=2024/month=12/day=*/data.parquet
└── electricity/year=2024/month=12/day=*/data.parquet

gold/
└── features/year=2024/month=12/features.parquet
```

---

## BƯỚC 7: TEST TỰ ĐỘNG TRIGGER

### 7.1. Chạy Ingestion Task thủ công

1. Vào ECS → Clusters → `vietnam-energy-cluster`

2. Run Ingestion task (DAILY mode)

3. Đợi task hoàn thành (5-10 phút)

### 7.2. Kiểm tra Processing Task tự động chạy

4. Sau khi Ingestion task ghi data vào Bronze

5. Trong vòng 1-2 phút, Processing task sẽ tự động chạy

6. Check ở tab **Tasks** → Tìm task mới với:
   - **Task definition**: `vietnam-energy-processing-task`
   - **Started by**: `ecs-scheduled-task` (từ EventBridge)

### 7.3. Verify luồng hoàn chỉnh

```
Ingestion Task (01:00 AM)
    ↓
Ghi Bronze data
    ↓
S3 Event → EventBridge
    ↓
Processing Task tự động chạy (~ 01:05 AM)
    ↓
Tạo Silver & Gold data
```

---

## 🎉 HOÀN THÀNH!

Hệ thống giờ đã:
- ✅ Thu thập dữ liệu (Ingestion - Bronze)
- ✅ Làm sạch dữ liệu (Processing - Silver)
- ✅ Tạo features cho ML (Processing - Gold)
- ✅ Tự động chạy liên tục

---

## 🔍 MONITORING

### CloudWatch Logs

🔗 CloudWatch Console → Log groups → `/ecs/vietnam-energy-processing`

### Xem logs của lần chạy gần nhất:

```powershell
aws logs tail /ecs/vietnam-energy-processing --follow --region ap-southeast-1
```

### Metrics để theo dõi:

1. **Task Duration**: Bao lâu mất để xử lý
2. **Success Rate**: % tasks thành công
3. **Data Volume**: Số rows trong Silver/Gold

---

## 💰 CHI PHÍ

| Service | Usage | Cost/Month |
|---------|-------|-----------|
| **ECS Fargate** (Processing) | 10 min/day @ 0.5 vCPU | ~$0.50 |
| **S3 Storage** (Silver + Gold) | ~30 GB | ~$0.70 |
| **CloudWatch Logs** | 2 GB/month | ~$1.00 |
| **EventBridge** | 30 events/month | Free |
| **Total (Processing only)** | | **~$2-3/month** |

**Combined with Ingestion**: ~$4-6/month total

---

## 🐛 TROUBLESHOOTING

### Task failed: "ModuleNotFoundError: No module named 'pandas'"

**Fix**: 
- Verify `requirements.txt` có `pandas`
- Rebuild Docker image
- Push lại lên ECR

---

### Task failed: "FileNotFoundError: Bronze data not found"

**Nguyên nhân**: Ingestion chưa chạy hoặc data chưa có

**Fix**:
1. Check S3 Bronze data có tồn tại không
2. Chạy Ingestion task trước
3. Verify S3 path trong config đúng chưa

---

### EventBridge không trigger

**Fix**:
1. Check S3 EventBridge notification đã enable chưa
2. Check EventBridge Rule có **Enabled** không
3. Check event pattern đúng bucket name chưa
4. Test bằng cách manual upload file vào Bronze

---

### Memory Error (OOM)

**Nguyên nhân**: Processing quá nhiều ngày cùng lúc

**Fix**:
- Tăng memory trong Task Definition (1 GB → 2 GB)
- Giảm `BACKFILL_CHUNK_DAYS` trong config
- Hoặc chạy BACKFILL từng đợt nhỏ

---

### Silver data có quá nhiều NaN

**Fix**:
1. Check Bronze data quality
2. Xem logs để tìm data quality issues
3. Adjust cleaning thresholds trong config

---

## 📞 NEXT STEPS

Sau khi Processing chạy ổn:

1. ✅ **Service Training** - Train ML model từ Gold features
2. ✅ **Service Dashboard** - Visualize predictions

Bạn muốn deploy Service Training tiếp không? 🚀