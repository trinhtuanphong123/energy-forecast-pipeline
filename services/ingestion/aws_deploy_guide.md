# 🚀 HƯỚNG DẪN DEPLOY SERVICE INGESTION (3 MODES) QUA AWS CONSOLE

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

## 🗺️ ROADMAP - 10 BƯỚC

```
1. Tạo S3 Bucket (nơi lưu dữ liệu)
2. Tạo ECR Repository (nơi lưu Docker image)
3. Build & Push Docker Image (từ máy local)
4. Lưu API Keys vào Secrets Manager
5. Tạo IAM Roles (quyền truy cập)
6. Tạo ECS Cluster
7. Tạo Task Definition
8. Chạy BACKFILL Task thủ công (1 lần)
9. Tạo EventBridge Schedule: HOURLY (mỗi giờ)
10. Tạo EventBridge Schedule: COMPACTION (mỗi ngày)
```

---

## BƯỚC 1-7: GIỐNG HỆT HƯỚNG DẪN CŨ

**Các bước 1-7 hoàn toàn giống với hướng dẫn cũ:**

1. ✅ Tạo S3 Bucket
2. ✅ Tạo ECR Repository
3. ✅ Build & Push Docker Image
4. ✅ Lưu API Keys vào Secrets Manager
5. ✅ Tạo IAM Roles (Task Role + Execution Role)
6. ✅ Tạo ECS Cluster
7. ✅ Tạo Task Definition

**Chú ý quan trọng ở Bước 7 (Task Definition):**

Khi tạo Environment Variables, thay đổi như sau:

| Key | Value Type | Value |
|-----|------------|-------|
| `MODE` | Value | `HOURLY` ← **Thay đổi từ DAILY** |
| `S3_BUCKET` | Value | `vietnam-energy-data-yourname` |
| `LOG_LEVEL` | Value | `INFO` |
| `VISUAL_CROSSING_API_KEY` | ValueFrom | `arn:aws:secretsmanager:...:VisualCrossingAPIKey` |
| `ELECTRICITY_MAPS_API_KEY` | ValueFrom | `arn:aws:secretsmanager:...:ElectricityMapsAPIKey` |

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

8. **Subnets**: Chọn **ít nhất 1 subnet**

9. **Security group**: 
   - Chọn **Create a new security group**
   - **Security group name**: `energy-ingestion-sg`
   - **Description**: `SG for Energy Ingestion Task`
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

17. **Status** sẽ thay đổi: `PROVISIONING` → `PENDING` → `RUNNING` → `STOPPED`

18. Click vào Task ID để xem chi tiết

19. Tab **Logs** → Bạn sẽ thấy logs real-time

### ⏱️ Thời gian:
- **BACKFILL sẽ chạy 2-3 giờ** (lấy dữ liệu từ 2021 đến hiện tại)

### 8.7. Kiểm tra dữ liệu trên S3

🔗 Vào S3 Console → Click vào bucket `vietnam-energy-data-yourname`

Bạn sẽ thấy cấu trúc (với file **data.json**):

```
bronze/
├── weather/
│   ├── year=2021/month=10/day=27/data.json
│   ├── year=2021/month=10/day=28/data.json
│   └── ...
└── electricity/
    ├── carbon_intensity/
    │   ├── year=2021/month=10/day=27/data.json
    │   └── ...
    └── ...
```

---

## BƯỚC 9: TẠO SCHEDULE HOURLY ⏰

> Schedule HOURLY = Tự động chạy task mỗi giờ để lấy dữ liệu giờ trước

### 9.1. Vào EventBridge Scheduler

🔗 https://ap-southeast-1.console.aws.amazon.com/scheduler/home?region=ap-southeast-1

Hoặc: AWS Console → Tìm "EventBridge" → Click **EventBridge Scheduler**

### 9.2. Create Schedule

1. Click **Create schedule**

### 9.3. Schedule Details

2. **Schedule name**: Nhập
   ```
   vietnam-energy-hourly-ingestion
   ```

3. **Description**: `Hourly ingestion task - runs every hour at :30`

4. **Schedule group**: **default**

### 9.4. Schedule Pattern

5. **Occurrence**: Chọn **Recurring schedule**

6. **Schedule type**: Chọn **Cron-based schedule**

7. **Cron expression**: Nhập
   ```
   30 * * * ? *
   ```
   
   > Giải thích: Chạy phút 30 mỗi giờ (ví dụ: 00:30, 01:30, 02:30, ...)

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

15. **VPC**: Chọn VPC mặc định

16. **Subnets**: Chọn subnet (same as Bước 8)

17. **Security groups**: Chọn `energy-ingestion-sg`

18. **Public IP**: Chọn **ENABLED**

### 9.7. Container Overrides (GIỮ MODE=HOURLY)

**Chú ý:** Không cần override gì vì Task Definition đã set `MODE=HOURLY` rồi!

### 9.8. Execution Role

19. Scroll xuống **Permissions**

20. **Execution role**: 
    - Chọn **Create new role for this schedule**

21. Click **Next**

### 9.9. Settings

22. **Timezone**: Chọn **UTC**

23. **Enable schedule**: ✅ Tick **Enabled**

24. **Retry policy**: Giữ mặc định

25. Click **Next**

### 9.10. Review and Create

26. Review lại thông tin → Click **Create schedule**

### ✅ Xác nhận:
- Status: **Enabled**
- Next run: Sẽ hiển thị thời gian chạy lần tiếp theo (ví dụ: 13:30 UTC)

---

## BƯỚC 10: TẠO SCHEDULE COMPACTION 🗜️

> Schedule COMPACTION = Tự động gộp hourly files của ngày hôm qua thành 1 file

### 10.1. Create Schedule

1. EventBridge Scheduler Console → Click **Create schedule**

### 10.2. Schedule Details

2. **Schedule name**: Nhập
   ```
   vietnam-energy-daily-compaction
   ```

3. **Description**: `Daily compaction task - compacts yesterday's hourly files`

4. **Schedule group**: **default**

### 10.3. Schedule Pattern

5. **Occurrence**: Chọn **Recurring schedule**

6. **Schedule type**: Chọn **Cron-based schedule**

7. **Cron expression**: Nhập
   ```
   0 18 * * ? *
   ```
   
   > Giải thích: 18:00 UTC = 01:00 AM Vietnam (UTC+7)
   > Chạy sau khi ngày hôm qua đã có đủ 24 hourly files

8. **Flexible time window**: Chọn **Off**

9. Click **Next**

### 10.4. Target

10. **Target API**: Chọn **AWS ECS**

11. **ECS cluster**: Chọn `vietnam-energy-cluster`

12. **ECS task definition**: 
    - **Family**: `vietnam-energy-ingestion-task`
    - **Revision**: **Latest**

13. **Launch type**: Chọn **FARGATE**

14. **Platform version**: **LATEST**

### 10.5. Networking

15. **VPC**: Chọn VPC mặc định

16. **Subnets**: Chọn subnet

17. **Security groups**: Chọn `energy-ingestion-sg`

18. **Public IP**: Chọn **ENABLED**

### 10.6. Container Overrides (OVERRIDE MODE=COMPACTION)

**⚠️ QUAN TRỌNG:** Phải override MODE thành COMPACTION!

19. Expand **Container overrides - optional**

20. Click vào `ingestion-container`

21. Scroll xuống **Environment variable overrides**

22. Click **Add environment variable**

23. Nhập:
    - **Key**: `MODE`
    - **Value**: `COMPACTION`

24. Click **Update**

### 10.7. Execution Role

25. **Execution role**: Chọn **Create new role for this schedule**

26. Click **Next**

### 10.8. Settings

27. **Timezone**: Chọn **UTC**

28. **Enable schedule**: ✅ Tick **Enabled**

29. Click **Next**

### 10.9. Review and Create

30. Review lại thông tin → Click **Create schedule**

### ✅ Xác nhận:
- Status: **Enabled**
- Next run: Sẽ hiển thị 18:00 UTC ngày tiếp theo

---

## 🎉 HOÀN THÀNH!

Hệ thống giờ đã:
- ✅ Có dữ liệu lịch sử từ 2021 (sau khi Backfill xong)
- ✅ Tự động thu thập dữ liệu mỗi giờ (HOURLY schedule)
- ✅ Tự động gộp files mỗi ngày (COMPACTION schedule)

---

## 🔍 KIỂM TRA HỆ THỐNG

### 1. Xem dữ liệu HOURLY trên S3

🔗 S3 Console → Click bucket → Browse:

**Trong ngày (trước compaction):**
```
bronze/
├── weather/year=2024/month=01/day=11/
│   ├── 00_30.json
│   ├── 01_30.json
│   ├── 02_30.json
│   └── ... (đang thu thập)
└── electricity/carbon_intensity/year=2024/month=01/day=11/
    ├── 00_30.json
    ├── 01_30.json
    └── ...
```

**Sau compaction (ngày hôm qua):**
```
bronze/
├── weather/year=2024/month=01/day=10/
│   └── data.json  ← GỘP TỪ 24 FILES
└── electricity/carbon_intensity/year=2024/month=01/day=10/
    └── data.json  ← GỘP TỪ 24 FILES
```

### 2. Xem logs

🔗 CloudWatch Logs Console → `/ecs/vietnam-energy-ingestion`

**HOURLY logs:**
```
☀️ Starting weather data ingestion (HOURLY) for 2024-01-11 13:00
✅ 2024-01-11 13:00 -> s3://.../13_30.json
```

**COMPACTION logs:**
```
🗜️ Starting full compaction for 2024-01-10
📁 Found 24 hourly files
✅ Compacted 24 hours -> s3://.../data.json
🗑️ Deleted 24/24 hourly files
```

### 3. Xem task history

🔗 ECS Console → Clusters → `vietnam-energy-cluster` → Tab **Tasks**

Bạn sẽ thấy 2 loại tasks:
- **HOURLY tasks**: Chạy mỗi giờ (24 tasks/ngày)
- **COMPACTION tasks**: Chạy 1 lần/ngày (lúc 01:00 AM)

### 4. Xem schedule status

🔗 EventBridge Scheduler Console

Bạn sẽ thấy 2 schedules:
- ✅ `vietnam-energy-hourly-ingestion` (State: ENABLED)
- ✅ `vietnam-energy-daily-compaction` (State: ENABLED)

---

## 💰 CHI PHÍ DỰ KIẾN

| Service | Usage | Cost/Month |
|---------|-------|-----------|
| **S3 Storage** | ~20 GB | ~$0.50 |
| **ECS Fargate (HOURLY)** | 24 tasks/day × 30s each | ~$2.00 |
| **ECS Fargate (COMPACTION)** | 1 task/day × 1 min each | ~$0.30 |
| **Secrets Manager** | 2 secrets | ~$0.80 |
| **CloudWatch Logs** | 2 GB/month | ~$1.00 |
| **ECR** | 1 image | Free |
| **EventBridge** | 2 rules | Free |
| **Total** | | **~$4-5/month** |

---

## 🐛 TROUBLESHOOTING

### Issue 1: HOURLY task fails "Hour not found"

**Nguyên nhân**: API chưa có dữ liệu cho giờ đó (delay)

**Fix**:
- Bình thường, sẽ retry giờ tiếp theo
- Hoặc chạy manual task với override hour khác

---

### Issue 2: COMPACTION fails "No hourly files found"

**Nguyên nhân**: Các HOURLY tasks của ngày hôm qua bị fail

**Fix**:
1. Check CloudWatch logs → Tìm giờ nào bị fail
2. Chạy manual HOURLY task để fill gap:
   - Run Task → Override `MODE=HOURLY`
   - Logs sẽ show giờ nào bị thiếu
3. Chạy lại COMPACTION task

---

### Issue 3: Duplicate data (có cả HH_30.json và data.json)

**Nguyên nhân**: COMPACTION chưa chạy hoặc failed

**Fix**:
1. Check COMPACTION schedule có enabled không
2. Check logs của COMPACTION task
3. Chạy manual COMPACTION task

---

### Issue 4: Task timeout

**Nguyên nhân**: Network issue hoặc API slow

**Fix**:
1. Check security group có allow outbound traffic
2. Check API status
3. Increase task timeout trong Task Definition

---

## 📊 WORKFLOW TIMELINE

### Ví dụ: Ngày 2024-01-11

```
00:00 ─────────────────────────────────────────────────
  │
00:30  ✅ HOURLY task chạy → Lấy data 00:00 → 00_30.json
  │
01:00  ✅ COMPACTION task chạy → Gộp dữ liệu ngày 2024-01-10
  │      - Input: 00_30.json, 01_30.json, ..., 23_30.json (của ngày 10)
  │      - Output: data.json (của ngày 10)
  │      - Delete: All HH_30.json files (của ngày 10)
  │
01:30  ✅ HOURLY task chạy → Lấy data 01:00 → 01_30.json
  │
02:30  ✅ HOURLY task chạy → Lấy data 02:00 → 02_30.json
  │
  │  ... (tiếp tục mỗi giờ)
  │
23:30  ✅ HOURLY task chạy → Lấy data 23:00 → 23_30.json
  │
24:00 ─────────────────────────────────────────────────
```

### Kết quả sau 24h:

**Ngày 2024-01-10 (đã compacted):**
```
bronze/weather/year=2024/month=01/day=10/data.json ✅
```

**Ngày 2024-01-11 (đang thu thập):**
```
bronze/weather/year=2024/month=01/day=11/
├── 00_30.json ✅
├── 01_30.json ✅
├── 02_30.json ✅
└── ... (tiếp tục đến 23_30.json)
```

---

## 🎯 CHECKLIST HOÀN THÀNH

- [ ] S3 Bucket đã tạo
- [ ] ECR Repository đã có Docker image
- [ ] API Keys đã lưu vào Secrets Manager
- [ ] IAM Roles đã tạo và có đủ quyền
- [ ] ECS Cluster đã tạo
- [ ] Task Definition đã tạo (MODE=HOURLY)
- [ ] BACKFILL task đã chạy xong (có data lịch sử)
- [ ] HOURLY schedule đã enabled (chạy mỗi giờ)
- [ ] COMPACTION schedule đã enabled (chạy mỗi ngày)
- [ ] CloudWatch Logs có dữ liệu
- [ ] S3 có cấu trúc đúng (HH_30.json cho ngày hôm nay, data.json cho ngày hôm qua)

---

## 📞 SUPPORT

**Nếu cần trợ giúp:**

1. **Check Logs đầu tiên**: 
   - CloudWatch Logs → `/ecs/vietnam-energy-ingestion`

2. **Check Task Status**:
   - ECS Console → Clusters → Tasks → Click vào task → Tab **Stopped reason**

3. **Common Issues**:
   - Hour not found → Bình thường, API delay
   - File already exists → Bình thường, skip
   - No hourly files found → Check HOURLY tasks của ngày hôm qua
   - API timeout → Retry

---

## 🎯 NEXT STEPS

Sau khi Service Ingestion chạy ổn:

1. ✅ **Monitor 1 tuần** - Đảm bảo không có gap trong dữ liệu
2. ✅ **Service Processing** - Làm sạch dữ liệu (Bronze → Silver → Gold)
3. ✅ **Service Training** - Train ML model
4. ✅ **Service Dashboard** - Visualize kết quả

Bạn có muốn tôi hướng dẫn tiếp không? 🚀