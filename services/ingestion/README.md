# ⚡ Service Ingestion - Vietnam Energy Forecasting

## 📋 Mô tả

Service Ingestion là thành phần đầu tiên trong pipeline, chịu trách nhiệm thu thập dữ liệu từ các API bên ngoài và lưu vào S3 Bronze Layer.

**Chức năng chính:**
- ☀️ Thu thập dữ liệu thời tiết từ Visual Crossing API
- ⚡ Thu thập dữ liệu điện năng từ Electricity Maps API
- 💾 Lưu trữ dữ liệu JSON với partitioning theo ngày
- 🔄 Hỗ trợ 2 modes: BACKFILL (lịch sử) và DAILY (hàng ngày)

---

## 🏗️ Kiến trúc

```
┌─────────────────────┐
│  Visual Crossing    │
│  API                │◄─────┐
└─────────────────────┘      │
                              │
┌─────────────────────┐      │    ┌──────────────┐
│  Electricity Maps   │      ├────│  API Clients │
│  API                │◄─────┘    │  (Retry)     │
└─────────────────────┘           └──────┬───────┘
                                         │
                                         ▼
                                  ┌──────────────┐
                                  │   S3 Writer  │
                                  └──────┬───────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │   S3 Bronze Layer   │
                              │  /weather/          │
                              │  /electricity/      │
                              └─────────────────────┘
```

---

## 📁 Cấu trúc thư mục

```
services/ingestion/
│
├── Dockerfile                  # 🐳 Container definition
├── requirements.txt            # 📦 Python dependencies
├── .env.example                # 🔑 Environment template
├── .dockerignore               # 🛡️ Exclude files
│
└── src/                        # 🧠 Source code
    ├── __init__.py
    ├── main.py                 # 🏁 Entry point
    ├── config.py               # ⚙️ Configuration management
    ├── s3_writer.py            # 💾 S3 writer with partitioning
    │
    └── api_clients/            # 📡 API client modules
        ├── __init__.py
        ├── base.py             # Base class (retry logic)
        ├── weather.py          # Visual Crossing client
        └── electricity.py      # Electricity Maps client
```

---

## 🚀 Quick Start

### 1. Local Development

#### Cài đặt dependencies:

```bash
cd services/ingestion
pip install -r requirements.txt
```

#### Cấu hình environment:

```bash
cp .env.example .env
# Sửa file .env, điền API keys
```

#### Chạy local:

```bash
# Mode DAILY (lấy dữ liệu hôm qua)
MODE=DAILY python src/main.py

# Mode BACKFILL (lấy dữ liệu lịch sử)
MODE=BACKFILL python src/main.py
```

### 2. Docker Local Test

#### Build image:

```bash
docker build -t vietnam-energy-ingestion:latest .
```

#### Run container:

```bash
docker run --rm \
  -e MODE=DAILY \
  -e VISUAL_CROSSING_API_KEY=your_key \
  -e ELECTRICITY_MAPS_API_KEY=your_key \
  -e S3_BUCKET=vietnam-energy-data \
  -e AWS_ACCESS_KEY_ID=your_id \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  vietnam-energy-ingestion:latest
```

### 3. AWS Deployment

Xem hướng dẫn chi tiết trong [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md)

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `MODE` | Execution mode: `BACKFILL` hoặc `DAILY` | Yes | `DAILY` |
| `VISUAL_CROSSING_API_KEY` | Visual Crossing API key | Yes | - |
| `ELECTRICITY_MAPS_API_KEY` | Electricity Maps API key | Yes | - |
| `S3_BUCKET` | S3 bucket name | Yes | `vietnam-energy-data` |
| `LOG_LEVEL` | Logging level | No | `INFO` |

### Mode Comparison

| Mode | Purpose | Frequency | Date Range |
|------|---------|-----------|------------|
| **BACKFILL** | Thu thập dữ liệu lịch sử | 1 lần duy nhất | 2021-01-01 đến hôm qua |
| **DAILY** | Thu thập dữ liệu mới | Hàng ngày (01:00 AM) | Chỉ hôm qua |

---

## 📊 Output Data Structure

### S3 Path Structure (Partitioning)

```
s3://vietnam-energy-data/
└── bronze/
    ├── weather/
    │   └── year=2024/
    │       └── month=12/
    │           └── day=20/
    │               └── data.json
    │
    └── electricity/
        ├── carbon_intensity/
        │   └── year=2024/
        │       └── month=12/
        │           └── day=20/
        │               └── data.json
        ├── total_load/
        ├── price_day_ahead/
        ├── electricity_mix/
        └── electricity_flows/
```

### Data Schema

#### Weather Data (weather/data.json)

```json
{
  "queryCost": 1,
  "latitude": 14.0583,
  "longitude": 108.2772,
  "resolvedAddress": "Vietnam",
  "timezone": "Asia/Bangkok",
  "days": [
    {
      "datetime": "2024-12-20",
      "temp": 25.5,
      "humidity": 75.2,
      "hours": [
        {
          "datetime": "00:00:00",
          "temp": 24.0,
          "humidity": 78.0,
          "precip": 0.0,
          "windspeed": 12.5,
          "cloudcover": 45.0
        }
      ]
    }
  ]
}
```

#### Electricity Data (electricity/{signal}/data.json)

```json
{
  "zone": "VN",
  "history": [
    {
      "datetime": "2024-12-20T00:00:00Z",
      "carbonIntensity": 450,
      "fossilFreePercentage": 35
    }
  ],
  "_metadata": {
    "signal": "carbon_intensity",
    "query_date": "2024-12-20",
    "zone": "VN"
  }
}
```

---

## 🔍 Monitoring & Logging

### CloudWatch Logs

Logs được ghi vào: `/ecs/vietnam-energy-ingestion`

### Log Levels

- `INFO`: Hoạt động bình thường
- `WARNING`: Vấn đề nhỏ (ví dụ: retry)
- `ERROR`: Lỗi nghiêm trọng (task sẽ fail)

### Xem logs:

```bash
# Tail logs realtime
aws logs tail /ecs/vietnam-energy-ingestion --follow

# Filter logs theo keyword
aws logs filter-log-events \
  --log-group-name /ecs/vietnam-energy-ingestion \
  --filter-pattern "ERROR"
```

---

## 🐛 Troubleshooting

### Issue: Task fails với "Permission denied"

**Solution:** Check IAM Role có policy ghi S3:

```bash
aws iam get-role-policy \
  --role-name EnergyIngestionTaskRole \
  --policy-name S3AccessPolicy
```

### Issue: API timeout

**Solution:** Increase retry count trong `config.py`:

```python
MAX_RETRIES = 5  # Default: 3
```

### Issue: Data bị duplicate

**Solution:** Check file đã tồn tại trước khi ghi:

```python
if s3_writer.check_file_exists(s3_key):
    logger.info("File exists, skipping...")
```

---

## 🧪 Testing

### Unit Tests

```bash
pytest tests/unit/
```

### Integration Tests

```bash
pytest tests/integration/
```

### Manual Test

```bash
# Test Weather API
python -c "
from src.api_clients.weather import WeatherAPIClient
client = WeatherAPIClient('YOUR_KEY', '...', 'Vietnam', 'temp')
data = client.fetch_data('2024-12-20')
print(data)
"
```

---

## 📈 Performance

- **Duration**: ~5-10 giây/ngày (DAILY mode)
- **Cost**: ~$0.01/tháng (Fargate Spot: 0.25 vCPU, 512 MB)
- **API Calls**: 
  - Weather: 1 request/ngày
  - Electricity: 5 requests/ngày (5 signals)

---

## 🔐 Security

- ✅ API keys lưu trong AWS Secrets Manager (không hardcode)
- ✅ IAM Role với least privilege principle
- ✅ S3 bucket không public
- ✅ CloudWatch Logs encrypted at rest

---

## 📝 TODO

- [ ] Add data validation schema (Pydantic)
- [ ] Add alerting khi task fail (SNS)
- [ ] Implement exponential backoff cho retry
- [ ] Add metrics tracking (success rate, latency)

---

## 👥 Contributors

- **Your Name** - Initial work

---

## 📄 License

MIT License