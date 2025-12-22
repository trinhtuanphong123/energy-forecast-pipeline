# 🚀 HƯỚNG DẪN DEPLOY SERVICE INGESTION QUA AWS CONSOLE (KHÔNG CODE)

> 💡 **Hướng dẫn này chỉ dùng giao diện web AWS Console - KHÔNG CẦN gõ lệnh!**

---

## 📋 Chuẩn bị

### Bạn cần có:
- ✅ AWS Account (đã đăng ký và đăng nhập)
- ✅ Visual Crossing API Key
- ✅ Electricity Maps API Key
- ✅ Docker Desktop đã cài trên máy Windows (để build image)

### Link đăng nhập AWS:
🔗 https://console.aws.amazon.com/

---

## 🗺️ ROADMAP - 9 BƯỚC

```
1. Tạo S3 Bucket (nơi lưu dữ liệu)
2. Tạo ECR Repository (nơi lưu Docker image)  
3. Build & Push Docker Image (từ máy local)
4. Lưu API Keys vào Secrets Manager
5. Tạo IAM Roles (quyền truy cập)
6. Tạo ECS Cluster
7. Tạo Task Definition
8. Chạy Task thủ công (BACKFILL - 1 lần)
9. Tạo Schedule tự động (DAILY - hàng ngày)
```

---

## BƯỚC 1: TẠO S3 BUCKET 🪣

### 1.1. Vào S3 Console

🔗 https://s3.console.aws.amazon.com/s3/home?region=ap-southeast-1

Hoặc: AWS Console → Tìm "S3" trong thanh search → Click **S3**

### 1.2. Tạo Bucket

1. Click nút **Create bucket** (màu cam)

2. **Bucket name**: Nhập tên (phải unique toàn cầu)
   ```
   vietnam-energy-data-yourname
   ```
   > Ví dụ: `vietnam-energy-data-john`, `vietnam-energy-data-nguyen`

3. **AWS Region**: Chọn **Asia Pacific (Singapore) ap-southeast-1**

4. **Object Ownership**: Giữ mặc định (**ACLs disabled**)

5. **Block Public Access settings**: 
   - ✅ Tick **Block all public access** (GIỮ NGUYÊN)

6. **Bucket Versioning**: Chọn **Disable**

7. **Default encryption**: Giữ mặc định (**Server-side encryption with Amazon S3 managed keys (SSE-S3)**)

8. Click **Create bucket**

### ✅ Xác nhận:
- Bạn sẽ thấy bucket mới trong danh sách
- Click vào bucket name để xem chi tiết

📝 **GHI LẠI**: Tên bucket (sẽ dùng ở bước sau)

---

## BƯỚC 2: TẠO ECR REPOSITORY 📦

### 2.1. Vào ECR Console

🔗 https://ap-southeast-1.console.aws.amazon.com/ecr/repositories?region=ap-southeast-1

Hoặc: AWS Console → Tìm "ECR" → Click **Elastic Container Registry**

### 2.2. Tạo Repository

1. Click **Get Started** hoặc **Create repository**

2. **Visibility settings**: Chọn **Private**

3. **Repository name**: Nhập
   ```
   vietnam-energy-ingestion
   ```

4. **Tag immutability**: Chọn **Disabled**

5. **Image scan settings**: 
   - ✅ Tick **Scan on push** (để tự động scan security)

6. **Encryption settings**: Giữ mặc định (**AES-256**)

7. Click **Create repository**

### 2.3. Lấy Repository URI

1. Click vào repository vừa tạo (`vietnam-energy-ingestion`)
2. Copy **URI** ở phần đầu trang
   ```
   123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-ingestion
   ```

📝 **GHI LẠI**: Repository URI (sẽ dùng ở bước 3)

---

## BƯỚC 3: BUILD & PUSH DOCKER IMAGE 🐳

> ⚠️ Bước này cần dùng PowerShell trên Windows

### 3.1. Mở PowerShell

- Windows Key + X → Chọn **Windows PowerShell (Admin)**

### 3.2. Di chuyển vào thư mục dự án

```powershell
cd C:\path\to\your\vietnam-energy-forecasting\services\ingestion
```

### 3.3. Build Docker Image

```powershell
docker build -t vietnam-energy-ingestion:latest .
```

Đợi 2-3 phút để build xong.

### 3.4. Login vào ECR

**Lấy AWS Account ID:**

1. Vào AWS Console
2. Click vào tên user ở góc phải trên
3. Copy **Account ID** (12 số)

**Chạy lệnh (thay YOUR_ACCOUNT_ID):**

```powershell
# Thay 123456789012 bằng Account ID của bạn
$AWS_ACCOUNT_ID = "123456789012"

# Login
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com"
```

Kết quả: `Login Succeeded`

### 3.5. Tag và Push Image

```powershell
# Tag image (thay YOUR_ACCOUNT_ID)
docker tag vietnam-energy-ingestion:latest "$AWS_ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-ingestion:latest"

# Push lên ECR
docker push "$AWS_ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-ingestion:latest"
```

Đợi 3-5 phút để push xong.

### ✅ Xác nhận:

Quay lại ECR Console → Refresh page → Bạn sẽ thấy image với tag `latest`

---

## BƯỚC 4: LƯU API KEYS VÀO SECRETS MANAGER 🔐

### 4.1. Vào Secrets Manager Console

🔗 https://ap-southeast-1.console.aws.amazon.com/secretsmanager/home?region=ap-southeast-1

Hoặc: AWS Console → Tìm "Secrets Manager"

### 4.2. Tạo Secret cho Visual Crossing

1. Click **Store a new secret**

2. **Secret type**: Chọn **Other type of secret**

3. **Key/value pairs**: 
   - Click **Plaintext** tab
   - Xóa hết nội dung, paste **chỉ API key** (không có dấu ngoặc kép)
   ```
   your_visual_crossing_api_key_here
   ```

4. **Encryption key**: Giữ mặc định (**aws/secretsmanager**)

5. Click **Next**

6. **Secret name**: Nhập
   ```
   VisualCrossingAPIKey
   ```

7. **Description**: (Optional) `API Key for Visual Crossing Weather API`

8. Click **Next** → **Next** → **Store**

### 4.3. Tạo Secret cho Electricity Maps

**Lặp lại bước 4.2** với:
- **Plaintext**: `your_electricity_maps_api_key_here`
- **Secret name**: `ElectricityMapsAPIKey`
- **Description**: `API Key for Electricity Maps API`

### 4.4. Lấy Secret ARNs

1. Click vào secret `VisualCrossingAPIKey`
2. Copy **Secret ARN** (dạng: `arn:aws:secretsmanager:ap-southeast-1:123456789012:secret:VisualCrossingAPIKey-AbCdEf`)
3. Lặp lại với `ElectricityMapsAPIKey`

📝 **GHI LẠI**: 2 Secret ARNs (sẽ dùng ở bước 7)

---

## BƯỚC 5: TẠO IAM ROLES 👤

### 5.1. Vào IAM Console

🔗 https://console.aws.amazon.com/iam/home

Hoặc: AWS Console → Tìm "IAM"

---

### 5.2. Tạo Task Role (Role cho container chạy)

#### A. Tạo Role

1. Click **Roles** (menu bên trái)
2. Click **Create role**

3. **Trusted entity type**: Chọn **AWS service**
4. **Use case**: Chọn **Elastic Container Service** → Chọn **Elastic Container Service Task**
5. Click **Next**

#### B. Add Permissions

6. Tìm và tick các policies sau (dùng search box):
   - ✅ `CloudWatchLogsFullAccess`
   - ✅ `SecretsManagerReadWrite`

7. Click **Next**

#### C. Name and Create

8. **Role name**: Nhập
   ```
   EnergyIngestionTaskRole
   ```

9. **Description**: `Role for Energy Ingestion ECS Task to access S3 and Secrets`

10. Click **Create role**

#### D. Add S3 Policy

11. Tìm role vừa tạo trong danh sách → Click vào `EnergyIngestionTaskRole`
12. Tab **Permissions** → Click **Add permissions** → **Create inline policy**
13. Click tab **JSON** và paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:HeadObject"
      ],
      "Resource": [
        "arn:aws:s3:::vietnam-energy-data-yourname",
        "arn:aws:s3:::vietnam-energy-data-yourname/*"
      ]
    }
  ]
}
```

> ⚠️ **Thay `vietnam-energy-data-yourname`** bằng tên bucket thật của bạn!

14. Click **Next** → Policy name: `S3AccessPolicy` → Click **Create policy**

#### E. Copy ARN

15. Quay lại role page → Copy **ARN** ở phần Summary
    ```
    arn:aws:iam::123456789012:role/EnergyIngestionTaskRole
    ```

📝 **GHI LẠI**: Task Role ARN

---

### 5.3. Tạo Execution Role (Role để ECS pull image)

#### A. Tạo Role

1. Click **Roles** → **Create role**

2. **Trusted entity type**: **AWS service**
3. **Use case**: **Elastic Container Service** → **Elastic Container Service Task**
4. Click **Next**

#### B. Add Permission

5. Tìm và tick policy:
   - ✅ `AmazonECSTaskExecutionRolePolicy`

6. Click **Next**

#### C. Name and Create

7. **Role name**: 
   ```
   EnergyIngestionExecutionRole
   ```

8. Click **Create role**

#### D. Copy ARN

9. Click vào role → Copy **ARN**
   ```
   arn:aws:iam::123456789012:role/EnergyIngestionExecutionRole
   ```

📝 **GHI LẠI**: Execution Role ARN

---

## BƯỚC 6: TẠO ECS CLUSTER 🎯

### 6.1. Vào ECS Console

🔗 https://ap-southeast-1.console.aws.amazon.com/ecs/v2/clusters?region=ap-southeast-1

Hoặc: AWS Console → Tìm "ECS"

### 6.2. Tạo Cluster

1. Click **Create cluster**

2. **Cluster name**: Nhập
   ```
   vietnam-energy-cluster
   ```

3. **Infrastructure**: Giữ mặc định (**AWS Fargate (serverless)**)

4. **Monitoring**: (Optional) Có thể tick **Use Container Insights** để theo dõi chi tiết

5. Click **Create**

### ✅ Xác nhận:
- Cluster status: **Active**

---

## BƯỚC 7: TẠO TASK DEFINITION 📋

### 7.1. Vào Task Definitions

ECS Console → Click **Task definitions** (menu bên trái) → Click **Create new task definition**

### 7.2. Configure Task Definition Family

1. **Task definition family**: Nhập
   ```
   vietnam-energy-ingestion-task
   ```

### 7.3. Infrastructure Requirements

2. **Launch type**: Chọn **AWS Fargate**

3. **Operating system/Architecture**: Chọn **Linux/X86_64**

4. **CPU**: Chọn **0.25 vCPU**

5. **Memory**: Chọn **0.5 GB**

6. **Task role**: Chọn `EnergyIngestionTaskRole` (tạo ở Bước 5.2)

7. **Task execution role**: Chọn `EnergyIngestionExecutionRole` (tạo ở Bước 5.3)

### 7.4. Container - 1

8. **Container name**: Nhập
   ```
   ingestion-container
   ```

9. **Image URI**: Paste URI từ Bước 2.3
   ```
   123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-ingestion:latest
   ```

10. **Essential container**: ✅ Tick **Yes**

### 7.5. Environment Variables

11. Scroll xuống phần **Environment variables**

12. Click **Add environment variable** và thêm từng cái:

| Key | Value Type | Value |
|-----|------------|-------|
| `MODE` | Value | `DAILY` |
| `S3_BUCKET` | Value | `vietnam-energy-data-yourname` |
| `LOG_LEVEL` | Value | `INFO` |
| `VISUAL_CROSSING_API_KEY` | ValueFrom | `arn:aws:secretsmanager:...:VisualCrossingAPIKey-xxxxx` |
| `ELECTRICITY_MAPS_API_KEY` | ValueFrom | `arn:aws:secretsmanager:...:ElectricityMapsAPIKey-xxxxx` |

> ⚠️ **Chú ý:**
> - 3 biến đầu chọn **Value**
> - 2 biến API Key chọn **ValueFrom** và paste Secret ARN từ Bước 4.4

### 7.6. Logging

13. Expand phần **Logging - optional**

14. **Log driver**: Chọn **awslogs**

15. Tick **Auto-configure CloudWatch Logs**

16. **Log group name**: Nhập
    ```
    /ecs/vietnam-energy-ingestion
    ```

### 7.7. Create

17. Scroll xuống cuối → Click **Create**

### ✅ Xác nhận:
- Status: **ACTIVE**
- Revision: **1**

---

## BƯỚC 8: CHẠY BACKFILL (1 LẦN) 🔄

> Backfill = Lấy toàn bộ dữ liệu lịch sử từ 2021 đến nay

### 8.1. Vào Cluster

1. ECS Console → **Clusters** → Click vào `vietnam-energy-cluster`

### 8.2. Run Task

2. Tab **Tasks** → Click **Run new task**

3. **Compute options**: Chọn **Launch type**

4. **Launch type**: Chọn **FARGATE**

5. **Platform version**: **LATEST**

6. **Task definition**: 
   - **Family**: `vietnam-energy-ingestion-task`
   - **Revision**: `1 (latest)`

### 8.3. Networking

7. **VPC**: Chọn VPC mặc định (default VPC)

8. **Subnets**: Chọn **ít nhất 1 subnet** (chọn subnet nào cũng được)

9. **Security group**: 
   - Chọn **Create a new security group**
   - **Security group name**: `energy-ingestion-sg`
   - **Description**: `SG for Energy Ingestion Task`
   - **Inbound rules**: Không cần add rule nào (để trống)
   - **Outbound rules**: Giữ mặc định (All traffic to 0.0.0.0/0)

10. **Public IP**: ✅ Tick **ENABLED** (bắt buộc để gọi API)

### 8.4. Container Overrides (QUAN TRỌNG!)

11. Expand phần **Container overrides - optional**

12. Click vào container name `ingestion-container`

13. Scroll xuống **Environment variable overrides**

14. Tìm biến `MODE` → Sửa **Value** thành:
    ```
    BACKFILL
    ```

15. Click **Update**

### 8.5. Chạy Task

16. Scroll xuống cuối → Click **Create**

### 8.6. Theo dõi Task

17. Bạn sẽ thấy task mới ở tab **Tasks**

18. **Status** sẽ thay đổi: `PROVISIONING` → `PENDING` → `RUNNING` → `STOPPED`

19. Click vào Task ID để xem chi tiết

20. Tab **Logs** → Bạn sẽ thấy logs real-time

### ⏱️ Thời gian:
- **BACKFILL sẽ chạy 30-60 phút** (lấy dữ liệu từ 2021-2024)

### 8.7. Xem Logs trong CloudWatch (Optional)

🔗 https://ap-southeast-1.console.aws.amazon.com/cloudwatch/home?region=ap-southeast-1#logsV2:log-groups

1. Click vào log group `/ecs/vietnam-energy-ingestion`
2. Click vào log stream mới nhất
3. Bạn sẽ thấy logs chi tiết:
   ```
   ☀️ Starting weather data ingestion for 1460 days
   📅 [1/1460] Processing 2021-01-01
   ✅ [1/1460] 2021-01-01 -> s3://...
   ...
   ```

### 8.8. Kiểm tra dữ liệu trên S3

🔗 Vào S3 Console → Click vào bucket `vietnam-energy-data-yourname`

Bạn sẽ thấy cấu trúc:
```
bronze/
├── weather/
│   └── year=2021/
│       └── month=01/
│           └── day=01/
│               └── data.json
└── electricity/
    ├── carbon_intensity/
    ├── total_load/
    └── ...
```

---

## BƯỚC 9: TẠO SCHEDULE TỰ ĐỘNG ⏰

> Schedule = Tự động chạy task mỗi ngày lúc 01:00 AM

### 9.1. Vào EventBridge Scheduler

🔗 https://ap-southeast-1.console.aws.amazon.com/scheduler/home?region=ap-southeast-1

Hoặc: AWS Console → Tìm "EventBridge" → Click **EventBridge Scheduler**

### 9.2. Create Schedule

1. Click **Create schedule**

### 9.3. Schedule Details

2. **Schedule name**: Nhập
   ```
   vietnam-energy-daily-ingestion
   ```

3. **Description**: (Optional) `Daily ingestion task at 1AM Vietnam time`

4. **Schedule group**: **default**

### 9.4. Schedule Pattern

5. **Occurrence**: Chọn **Recurring schedule**

6. **Schedule type**: Chọn **Cron-based schedule**

7. **Cron expression**: Nhập
   ```
   0 18 * * ? *
   ```
   
   > Giải thích: 18:00 UTC = 01:00 AM Vietnam (UTC+7)

8. **Flexible time window**: Chọn **Off**

9. Click **Next**

### 9.5. Target

10. **Target API**: Chọn **AWS ECS**

11. **ECS cluster**: Chọn `vietnam-energy-cluster`

12. **ECS task definition**: 
    - **Family**: `vietnam-energy-ingestion-task`
    - **Revision**: **Latest**

13. **Launch type**: Chọn **FARGATE**

14. **Platform version**: **LATEST**

### 9.6. Networking

15. **VPC**: Chọn VPC mặc định (same as Bước 8)

16. **Subnets**: Chọn subnet (same as Bước 8)

17. **Security groups**: Chọn `energy-ingestion-sg` (tạo ở Bước 8)

18. **Public IP**: Chọn **ENABLED**

### 9.7. Execution Role

19. Scroll xuống **Permissions**

20. **Execution role**: 
    - Chọn **Create new role for this schedule**
    - Để EventBridge tự động tạo role

21. Click **Next**

### 9.8. Settings

22. **Timezone**: Chọn **UTC** (vì đã tính trong cron)

23. **Enable schedule**: ✅ Tick **Enabled**

24. **Retry policy**: Giữ mặc định
    - **Maximum age of event**: 24 hours
    - **Retry attempts**: 0

25. Click **Next**

### 9.9. Review and Create

26. Review lại thông tin → Click **Create schedule**

### ✅ Xác nhận:
- Status: **Enabled**
- Next run: Sẽ hiển thị thời gian chạy lần tiếp theo

---

## 🎉 HOÀN THÀNH!

Hệ thống giờ đã:
- ✅ Có dữ liệu lịch sử từ 2021-2024 (sau khi Backfill xong)
- ✅ Tự động chạy mỗi ngày lúc 01:00 AM
- ✅ Lưu dữ liệu vào S3 với cấu trúc rõ ràng

---

## 🔍 KIỂM TRA HỆ THỐNG

### 1. Xem dữ liệu trên S3

🔗 S3 Console → Click bucket → Browse:
```
bronze/
├── weather/year=2024/month=12/day=22/data.json
└── electricity/carbon_intensity/year=2024/month=12/day=22/data.json
```

### 2. Xem logs

🔗 CloudWatch Logs Console → `/ecs/vietnam-energy-ingestion`

### 3. Xem task history

🔗 ECS Console → Clusters → `vietnam-energy-cluster` → Tab **Tasks**

Filter by: **Stopped** để xem các task đã chạy

### 4. Xem schedule status

🔗 EventBridge Scheduler Console → `vietnam-energy-daily-ingestion`

---

## 💰 CHI PHÍ DỰ KIẾN

| Service | Usage | Cost/Month |
|---------|-------|-----------|
| **S3 Storage** | ~20 GB | ~$0.50 |
| **ECS Fargate** | 5 min/day | ~$0.30 |
| **Secrets Manager** | 2 secrets | ~$0.80 |
| **CloudWatch Logs** | 1 GB/month | ~$0.50 |
| **ECR** | 1 image | Free (500MB free tier) |
| **EventBridge** | 1 rule | Free |
| **Total** | | **~$2-3/month** |

---

## 🐛 TROUBLESHOOTING

### Task failed: "CannotPullContainerError"

**Nguyên nhân**: ECS không pull được image từ ECR

**Fix**:
1. Vào IAM → Roles → `EnergyIngestionExecutionRole`
2. Check có policy `AmazonECSTaskExecutionRolePolicy`
3. Nếu không có → Add permissions → Attach policy → Chọn `AmazonECSTaskExecutionRolePolicy`

---

### Task failed: "Essential container exited"

**Nguyên nhân**: Container chạy và exit với error

**Fix**:
1. Vào CloudWatch Logs → `/ecs/vietnam-energy-ingestion`
2. Xem log stream mới nhất để tìm lỗi cụ thể
3. Thường là:
   - API Key sai → Check Secrets Manager
   - Không ghi được S3 → Check Task Role có S3 policy
   - Network error → Check Public IP đã ENABLED chưa

---

### Schedule không chạy

**Fix**:
1. Vào EventBridge Scheduler → Click vào schedule
2. Check **State**: Phải là **ENABLED**
3. Check **Next run time**: Phải có giá trị
4. Check **Target**: Phải đúng cluster và task definition
5. Check **Execution role**: Phải có quyền chạy ECS task

---

### Không thấy logs trong CloudWatch

**Fix**:
1. Vào CloudWatch Logs
2. Check log group `/ecs/vietnam-energy-ingestion` đã tồn tại chưa
3. Nếu chưa có → Tạo manual:
   - CloudWatch → Logs → Log groups → Create log group
   - Log group name: `/ecs/vietnam-energy-ingestion`

---

## 📞 SUPPORT

**Nếu cần trợ giúp:**

1. **Check Logs đầu tiên**: 
   - CloudWatch Logs → `/ecs/vietnam-energy-ingestion`

2. **Check Task Status**:
   - ECS Console → Clusters → Tasks → Click vào task → Tab **Stopped reason**

3. **Common Issues**:
   - API timeout → Bình thường, sẽ retry
   - 401 Unauthorized → API key sai
   - 403 Forbidden → IAM role không đủ quyền
   - 500 Server Error → API provider lỗi, retry sau

---

## 🎯 NEXT STEPS

Sau khi Service Ingestion chạy ổn:

1. ✅ **Service Processing** - Làm sạch dữ liệu (Bronze → Silver → Gold)
2. ✅ **Service Training** - Train ML model
3. ✅ **Service Dashboard** - Visualize kết quả

Bạn có muốn tôi hướng dẫn tiếp không? 🚀