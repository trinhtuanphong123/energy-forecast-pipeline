# 🚀 DEPLOYMENT GUIDE - DASHBOARD SERVICE (AWS CONSOLE)

> **Mục tiêu**: Deploy Streamlit dashboard lên EC2 Free Tier (Always On)

---

## 📋 Prerequisites

- ✅ Service Training đã chạy và có model trong S3
- ✅ S3 có dữ liệu: predictions/, models/, gold/
- ✅ IAM Role với quyền đọc S3

---

## 🗺️ ROADMAP - 5 BƯỚC

```
1. Tạo EC2 Instance (Free Tier)
2. Install Dependencies (Docker, AWS CLI)
3. Build & Deploy Container
4. Configure Auto-Start
5. Access Dashboard
```

---

## BƯỚC 1: TẠO EC2 INSTANCE

### 1.1. Vào EC2 Console

🔗 https://ap-southeast-1.console.aws.amazon.com/ec2/home?region=ap-southeast-1

### 1.2. Launch Instance

1. Click **Launch instances**

2. **Name**: 
   ```
   vietnam-energy-dashboard
   ```

3. **Application and OS Images (Amazon Machine Image)**:
   - Quick Start: **Amazon Linux 2023**
   - AMI: Amazon Linux 2023 AMI (Free tier eligible)

4. **Instance type**:
   - **t2.micro** ✅ Free tier eligible
   - vCPU: 1, Memory: 1 GB

5. **Key pair (login)**:
   - Click **Create new key pair**
   - Key pair name: `vietnam-energy-key`
   - Key pair type: RSA
   - Format: `.pem` (for SSH)
   - Click **Create key pair**
   - **⚠️ Save file an toàn!** Không mất được

6. **Network settings**:
   - ✅ Allow SSH traffic from **Anywhere** (0.0.0.0/0)
   - ✅ Allow HTTP traffic from **Anywhere**
   - ✅ Allow HTTPS traffic from **Anywhere**

7. **Configure storage**:
   - **8 GB** gp3 (Free tier: up to 30 GB)

8. **Advanced details**:
   - **IAM instance profile**: `EnergyIngestionTaskRole` (dùng chung)
   - Để instance có quyền đọc S3

9. Click **Launch instance**

### 1.3. Wait & Note Public IP

- Đợi 2-3 phút cho instance khởi động
- Status: **Running** ✅
- **Copy Public IPv4 address** (ví dụ: `52.74.123.45`)

📝 **GHI LẠI**: Public IP

---

## BƯỚC 2: CONNECT & INSTALL

### 2.1. Connect to EC2

#### Windows (PowerShell):

```powershell
# Navigate to folder chứa key file
cd C:\Users\YourName\Downloads

# Connect
ssh -i vietnam-energy-key.pem ec2-user@52.74.123.45
```

Nếu lỗi permissions:
```powershell
icacls vietnam-energy-key.pem /inheritance:r
icacls vietnam-energy-key.pem /grant:r "%USERNAME%:R"
```

### 2.2. Install Docker

```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install docker -y

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -a -G docker ec2-user

# Logout and login again (hoặc chạy newgrp)
exit
# SSH lại
ssh -i vietnam-energy-key.pem ec2-user@52.74.123.45

# Verify
docker --version
```

### 2.3. Install Git

```bash
sudo yum install git -y
git --version
```

---

## BƯỚC 3: BUILD & DEPLOY

### 3.1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/vietnam-energy-forecasting.git
cd vietnam-energy-forecasting/services/dashboard
```

### 3.2. Create .env File

```bash
cat > .env << 'EOF'
S3_BUCKET=vietnam-energy-data-yourname
AWS_REGION=ap-southeast-1
STREAMLIT_SERVER_PORT=8501
EOF
```

⚠️ **Thay `vietnam-energy-data-yourname`** bằng tên bucket thật!

### 3.3. Build Docker Image

```bash
docker build -t vietnam-energy-dashboard:latest .
```

⏱️ Mất 3-5 phút

### 3.4. Run Container

```bash
docker run -d \
  --name energy-dashboard \
  --restart unless-stopped \
  -p 8501:8501 \
  --env-file .env \
  vietnam-energy-dashboard:latest
```

**Giải thích:**
- `-d`: Chạy background
- `--restart unless-stopped`: Auto-restart nếu crash
- `-p 8501:8501`: Map port
- `--env-file .env`: Load environment variables

### 3.5. Check Logs

```bash
# View logs
docker logs -f energy-dashboard

# Should see:
# You can now view your Streamlit app in your browser.
# Network URL: http://0.0.0.0:8501
```

---

## BƯỚC 4: CONFIGURE SECURITY GROUP

### 4.1. Vào EC2 Console → Instances

Click vào instance `vietnam-energy-dashboard`

### 4.2. Tab Security → Security groups

Click vào Security Group name

### 4.3. Edit Inbound Rules

1. Click **Edit inbound rules**

2. Click **Add rule**:
   - **Type**: Custom TCP
   - **Port range**: `8501`
   - **Source**: Anywhere IPv4 (0.0.0.0/0)
   - **Description**: Streamlit Dashboard

3. Click **Save rules**

---

## BƯỚC 5: ACCESS DASHBOARD

### 5.1. Open Browser

Navigate to:
```
http://YOUR_EC2_PUBLIC_IP:8501
```

Ví dụ: `http://52.74.123.45:8501`

### 5.2. Verify

Bạn sẽ thấy:
- ⚡ Vietnam Energy Forecasting header
- 3 tabs: Forecast, Model Performance, Data Explorer
- KPI cards với số liệu
- Charts với dữ liệu

---

## 🔧 TROUBLESHOOTING

### Dashboard không load

**Check container:**
```bash
docker ps  # Should see energy-dashboard running
docker logs energy-dashboard  # Check errors
```

**Common issues:**
- Port 8501 not open → Check Security Group
- Container crashed → Check logs
- No data → Verify S3 bucket name in .env

---

### Cannot connect S3

**Check IAM Role:**
```bash
# On EC2, check if can access S3
aws s3 ls s3://vietnam-energy-data-yourname/

# If error, IAM role not attached properly
```

**Fix:**
1. EC2 Console → Instances
2. Select instance → Actions → Security → Modify IAM role
3. Choose `EnergyIngestionTaskRole`
4. Restart container: `docker restart energy-dashboard`

---

### Streamlit shows "File not found"

**Cause**: No data in S3

**Fix:**
1. Run Training service first (creates predictions/)
2. Verify:
```bash
aws s3 ls s3://vietnam-energy-data-yourname/predictions/latest/
aws s3 ls s3://vietnam-energy-data-yourname/models/xgboost/latest/
```

---

## 🔄 UPDATE DASHBOARD

### When you push new code:

```bash
# SSH to EC2
ssh -i vietnam-energy-key.pem ec2-user@52.74.123.45

# Navigate to repo
cd vietnam-energy-forecasting/services/dashboard

# Pull latest code
git pull origin main

# Rebuild image
docker build -t vietnam-energy-dashboard:latest .

# Restart container
docker stop energy-dashboard
docker rm energy-dashboard

docker run -d \
  --name energy-dashboard \
  --restart unless-stopped \
  -p 8501:8501 \
  --env-file .env \
  vietnam-energy-dashboard:latest
```

---

## 💰 COST ESTIMATE

| Service | Usage | Cost/Month |
|---------|-------|-----------|
| **EC2 t2.micro** | 24/7 | **FREE** (12 months) |
| **EC2 after 12 months** | 24/7 | ~$8-10/month |
| **EBS Storage** | 8 GB | **FREE** (30 GB free tier) |
| **Data Transfer** | Minimal | **FREE** (1 GB free tier) |

**Total First Year**: **$0/month** ✅  
**Total After First Year**: ~$8-10/month

---

## 🎨 CUSTOMIZATION

### Change Theme

Edit `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#FF6B6B"  # Your color
backgroundColor = "#0e1117"
```

Rebuild and restart container.

### Add Custom Domain (Optional)

1. Buy domain (example.com)
2. Point A record to EC2 IP
3. Install Nginx + SSL:

```bash
sudo yum install nginx -y
# Configure reverse proxy
# Install Let's Encrypt SSL
```

---

## 📊 MONITORING

### Check Dashboard Health

```bash
# Container status
docker ps

# Container logs
docker logs energy-dashboard

# Container stats
docker stats energy-dashboard
```

### Check EC2 Metrics

- EC2 Console → Instances → Monitoring tab
- CloudWatch: CPU, Network, Disk metrics

---

## 🎉 HOÀN THÀNH!

Hệ thống giờ đã **HOÀN TOÀN TỰ ĐỘNG**:

```
01:00 AM Daily:
  └─ Ingestion collects data → Bronze

~01:05 AM:
  └─ Processing transforms → Silver + Gold

02:00 AM Sunday:
  └─ Training trains model → predictions/latest/

24/7:
  └─ Dashboard displays results (auto-refresh 5 min)
```

### 🔗 Access Points

- **Dashboard**: `http://YOUR_EC2_IP:8501`
- **SSH**: `ssh -i key.pem ec2-user@YOUR_EC2_IP`

### ✅ Verification Checklist

```
☐ Can access dashboard via browser
☐ See KPI metrics
☐ See forecast chart
☐ See model performance metrics
☐ Can download data CSV
☐ Dashboard auto-refreshes
```

---

## 🚀 NEXT STEPS

1. ✅ **Monitor Performance**: Track dashboard usage
2. ✅ **Setup Alerts**: CloudWatch alarms for EC2 health
3. ✅ **Add Authentication**: Implement user login (future)
4. ✅ **Custom Domain**: Add proper domain name (future)
5. ✅ **HTTPS**: Add SSL certificate (future)

---

Congratulations! 🎊 Bạn đã hoàn thành toàn bộ **4 Services** của Vietnam Energy Forecasting Platform! 🇻🇳⚡