# 🚀 HƯỚNG DẪN DEPLOY SERVICE INGESTION LÊN AWS

## 📋 Mục Lục
1. [Prerequisites](#prerequisites)
2. [Bước 1: Tạo S3 Bucket](#step-1-s3)
3. [Bước 2: Tạo ECR Repository](#step-2-ecr)
4. [Bước 3: Tạo IAM Role](#step-3-iam)
5. [Bước 4: Build & Push Docker Image](#step-4-docker)
6. [Bước 5: Tạo ECS Cluster](#step-5-ecs-cluster)
7. [Bước 6: Tạo ECS Task Definition](#step-6-task-definition)
8. [Bước 7: Chạy Backfill (1 lần)](#step-7-backfill)
9. [Bước 8: Tạo EventBridge Schedule](#step-8-eventbridge)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- AWS Account đã kích hoạt
- AWS CLI đã cài đặt: `aws --version`
- Docker đã cài đặt: `docker --version`
- API Keys đã có:
  - Visual Crossing API Key
  - Electricity Maps API Key

---

## Step 1: Tạo S3 Bucket {#step-1-s3}

### Option A: Qua AWS Console

1. Vào **S3 Console**: https://s3.console.aws.amazon.com/
2. Click **Create bucket**
3. Nhập thông tin:
   - **Bucket name**: `vietnam-energy-data` (phải unique toàn cầu)
   - **Region**: `ap-southeast-1` (Singapore)
   - **Block Public Access**: Để mặc định (block all)
4. Click **Create bucket**

### Option B: Qua AWS CLI

```bash
aws s3 mb s3://vietnam-energy-data --region ap-southeast-1
```

### Xác nhận bucket đã tạo:

```bash
aws s3 ls
```

---

## Step 2: Tạo ECR Repository {#step-2-ecr}

ECR (Elastic Container Registry) là nơi chứa Docker Image.

### Tạo repository:

```bash
aws ecr create-repository \
    --repository-name vietnam-energy-ingestion \
    --region ap-southeast-1
```

**Output mẫu:**
```json
{
    "repository": {
        "repositoryUri": "123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-ingestion"
    }
}
```

📝 **Ghi lại `repositoryUri` này, sẽ dùng ở bước sau!**

---

## Step 3: Tạo IAM Role {#step-3-iam}

IAM Role cho phép ECS Task ghi vào S3 và ghi logs vào CloudWatch.

### 3.1. Tạo Trust Policy

Tạo file `trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### 3.2. Tạo Role:

```bash
aws iam create-role \
    --role-name EnergyIngestionTaskRole \
    --assume-role-policy-document file://trust-policy.json
```

### 3.3. Tạo Policy cho S3 Access

Tạo file `s3-policy.json`:

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
        "arn:aws:s3:::vietnam-energy-data",
        "arn:aws:s3:::vietnam-energy-data/*"
      ]
    }
  ]
}
```

### 3.4. Attach Policy vào Role:

```bash
# S3 Policy
aws iam put-role-policy \
    --role-name EnergyIngestionTaskRole \
    --policy-name S3AccessPolicy \
    --policy-document file://s3-policy.json

# CloudWatch Logs Policy (managed)
aws iam attach-role-policy \
    --role-name EnergyIngestionTaskRole \
    --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
```

### 3.5. Tạo Execution Role (cho ECS Pull image từ ECR)

```bash
aws iam create-role \
    --role-name EnergyIngestionExecutionRole \
    --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
    --role-name EnergyIngestionExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

---

## Step 4: Build & Push Docker Image {#step-4-docker}

### 4.1. Authenticate Docker với ECR:

```bash
aws ecr get-login-password --region ap-southeast-1 | \
    docker login --username AWS --password-stdin \
    123456789012.dkr.ecr.ap-southeast-1.amazonaws.com
```

⚠️ **Thay `123456789012` bằng AWS Account ID của bạn!**

### 4.2. Build Docker Image:

Ở thư mục `services/ingestion/`:

```bash
docker build -t vietnam-energy-ingestion:latest .
```

### 4.3. Tag Image:

```bash
docker tag vietnam-energy-ingestion:latest \
    123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-ingestion:latest
```

### 4.4. Push lên ECR:

```bash
docker push \
    123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-ingestion:latest
```

### 4.5. Xác nhận image đã push:

```bash
aws ecr describe-images \
    --repository-name vietnam-energy-ingestion \
    --region ap-southeast-1
```

---

## Step 5: Tạo ECS Cluster {#step-5-ecs-cluster}

### Tạo cluster (Fargate):

```bash
aws ecs create-cluster \
    --cluster-name vietnam-energy-cluster \
    --region ap-southeast-1
```

---

## Step 6: Tạo ECS Task Definition {#step-6-task-definition}

Task Definition = "Bản thiết kế" cho container (RAM, CPU, Environment Variables).

### 6.1. Tạo file `task-definition.json`:

```json
{
  "family": "vietnam-energy-ingestion-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::123456789012:role/EnergyIngestionExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789012:role/EnergyIngestionTaskRole",
  "containerDefinitions": [
    {
      "name": "ingestion-container",
      "image": "123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/vietnam-energy-ingestion:latest",
      "essential": true,
      "environment": [
        {
          "name": "MODE",
          "value": "DAILY"
        },
        {
          "name": "S3_BUCKET",
          "value": "vietnam-energy-data"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "VISUAL_CROSSING_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:ap-southeast-1:123456789012:secret:VisualCrossingAPIKey-xxxxxx"
        },
        {
          "name": "ELECTRICITY_MAPS_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:ap-southeast-1:123456789012:secret:ElectricityMapsAPIKey-xxxxxx"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/vietnam-energy-ingestion",
          "awslogs-region": "ap-southeast-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

⚠️ **Thay thế:**
- `123456789012` → AWS Account ID của bạn
- `secret ARNs` → ARNs của secrets (xem bước 6.2)

### 6.2. Tạo Secrets trong AWS Secrets Manager:

```bash
# Visual Crossing API Key
aws secretsmanager create-secret \
    --name VisualCrossingAPIKey \
    --secret-string "YOUR_VISUAL_CROSSING_API_KEY" \
    --region ap-southeast-1

# Electricity Maps API Key
aws secretsmanager create-secret \
    --name ElectricityMapsAPIKey \
    --secret-string "YOUR_ELECTRICITY_MAPS_API_KEY" \
    --region ap-southeast-1
```

Lấy ARN của secrets:

```bash
aws secretsmanager describe-secret --secret-id VisualCrossingAPIKey --region ap-southeast-1
aws secretsmanager describe-secret --secret-id ElectricityMapsAPIKey --region ap-southeast-1
```

Copy ARN vào `task-definition.json`.

### 6.3. Tạo CloudWatch Log Group:

```bash
aws logs create-log-group \
    --log-group-name /ecs/vietnam-energy-ingestion \
    --region ap-southeast-1
```

### 6.4. Register Task Definition:

```bash
aws ecs register-task-definition \
    --cli-input-json file://task-definition.json \
    --region ap-southeast-1
```

---

## Step 7: Chạy Backfill (1 lần) {#step-7-backfill}

### 7.1. Tạo override file `backfill-override.json`:

```json
{
  "containerOverrides": [
    {
      "name": "ingestion-container",
      "environment": [
        {
          "name": "MODE",
          "value": "BACKFILL"
        }
      ]
    }
  ]
}
```

### 7.2. Chạy Backfill Task (thủ công):

```bash
aws ecs run-task \
    --cluster vietnam-energy-cluster \
    --launch-type FARGATE \
    --task-definition vietnam-energy-ingestion-task \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxx],securityGroups=[sg-xxxxxx],assignPublicIp=ENABLED}" \
    --overrides file://backfill-override.json \
    --region ap-southeast-1
```

⚠️ **Thay thế:**
- `subnet-xxxxxx` → Subnet ID của VPC (lấy từ VPC Console)
- `sg-xxxxxx` → Security Group ID (cho phép outbound traffic)

### 7.3. Theo dõi logs:

```bash
aws logs tail /ecs/vietnam-energy-ingestion --follow --region ap-southeast-1
```

---

## Step 8: Tạo EventBridge Schedule (Chạy hàng ngày) {#step-8-eventbridge}

### 8.1. Tạo IAM Role cho EventBridge:

Tạo file `eventbridge-trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "scheduler.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Tạo role:

```bash
aws iam create-role \
    --role-name EventBridgeSchedulerRole \
    --assume-role-policy-document file://eventbridge-trust-policy.json

# Attach policy cho phép run ECS tasks
aws iam attach-role-policy \
    --role-name EventBridgeSchedulerRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
```

### 8.2. Tạo Schedule:

```bash
aws scheduler create-schedule \
    --name vietnam-energy-daily-ingestion \
    --schedule-expression "cron(0 18 * * ? *)" \
    --schedule-expression-timezone "UTC" \
    --flexible-time-window Mode=OFF \
    --target '{
        "Arn": "arn:aws:ecs:ap-southeast-1:123456789012:cluster/vietnam-energy-cluster",
        "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSchedulerRole",
        "EcsParameters": {
            "TaskDefinitionArn": "arn:aws:ecs:ap-southeast-1:123456789012:task-definition/vietnam-energy-ingestion-task",
            "LaunchType": "FARGATE",
            "NetworkConfiguration": {
                "awsvpcConfiguration": {
                    "Subnets": ["subnet-xxxxxx"],
                    "SecurityGroups": ["sg-xxxxxx"],
                    "AssignPublicIp": "ENABLED"
                }
            }
        }
    }' \
    --region ap-southeast-1
```

**Giải thích Cron Expression:**
- `cron(0 18 * * ? *)` = 18:00 UTC = 01:00 AM Vietnam Time (UTC+7)

---

## Troubleshooting

### 1. Task không chạy được:

**Check logs:**
```bash
aws logs tail /ecs/vietnam-energy-ingestion --follow --region ap-southeast-1
```

**Check task status:**
```bash
aws ecs list-tasks --cluster vietnam-energy-cluster --region ap-southeast-1
aws ecs describe-tasks --cluster vietnam-energy-cluster --tasks TASK_ARN --region ap-southeast-1
```

### 2. Không kết nối được Internet:

- Đảm bảo Subnet có NAT Gateway hoặc Internet Gateway
- Hoặc set `assignPublicIp=ENABLED` trong network config

### 3. Permission denied khi ghi S3:

- Check IAM Role có policy đúng không
- Check bucket name có đúng không

### 4. API Key không hoạt động:

- Check Secrets Manager có đúng ARN không
- Check Task Role có quyền đọc Secrets Manager không

---

## 🎉 Hoàn thành!

Giờ hệ thống sẽ:
1. ✅ Chạy BACKFILL 1 lần (lấy dữ liệu 2021-2024)
2. ✅ Tự động chạy DAILY mỗi 01:00 AM Vietnam Time
3. ✅ Lưu dữ liệu vào S3 Bronze Layer với partitioning

**Kiểm tra dữ liệu trên S3:**

```bash
aws s3 ls s3://vietnam-energy-data/bronze/weather/ --recursive
aws s3 ls s3://vietnam-energy-data/bronze/electricity/ --recursive
```