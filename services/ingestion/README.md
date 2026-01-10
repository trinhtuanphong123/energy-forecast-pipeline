# ⚡ Service Ingestion - Vietnam Energy Forecasting

## 📋 Mô tả

Service Ingestion là thành phần đầu tiên trong pipeline, chịu trách nhiệm thu thập dữ liệu từ các API bên ngoài và lưu vào S3 Bronze Layer.

**Chức năng chính:**
- ☀️ Thu thập dữ liệu thời tiết từ Visual Crossing API
- ⚡ Thu thập dữ liệu điện năng từ Electricity Maps API
- 💾 Lưu trữ dữ liệu JSON với partitioning theo năm/tháng/ngày/giờ
- 🔄 Hỗ trợ 3 modes: **BACKFILL**, **HOURLY**, **COMPACTION**

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
                              │    - HH_30.json     │ (hourly)
                              │    - data.json      │ (compacted)
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
    ├── main.py                 # 🏁 Entry point (3 modes)
    ├── config.py               # ⚙️ Configuration management
    ├── s3_writer.py            # 💾 S3 writer with partitioning
    ├── compactor.py            # 🗜️ Hourly files compactor (NEW)
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
# Mode BACKFILL (lấy dữ liệu lịch sử)
MODE=BACKFILL python src/main.py

# Mode HOURLY (lấy dữ liệu giờ trước)
MODE=HOURLY python src/main.py

# Mode COMPACTION (gộp hourly files của ngày hôm qua)
MODE=COMPACTION python src/main.py
```

### 2. Docker Local Test

#### Build image:

```bash
docker build -t vietnam-energy-ingestion:latest .
```

#### Run container:

```bash
# BACKFILL mode
docker run --rm \
  -e MODE=BACKFILL \
  -e VISUAL_CROSSING_API_KEY=your_key \
  -e ELECTRICITY_MAPS_API_KEY=your_key \
  -e S3_BUCKET=vietnam-energy-data \
  -e AWS_ACCESS_KEY_ID=your_id \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  vietnam-energy-ingestion:latest

# HOURLY mode
docker run --rm \
  -e MODE=HOURLY \
  -e VISUAL_CROSSING_API_KEY=your_key \
  -e ELECTRICITY_MAPS_API_KEY=your_key \
  -e S3_BUCKET=vietnam-energy-data \
  vietnam-energy-ingestion:latest

# COMPACTION mode (không cần API keys)
docker run --rm \
  -e MODE=COMPACTION \
  -e S3_BUCKET=vietnam-energy-data \
  vietnam-energy-ingestion:latest
```

### 3. AWS Deployment

Xem hướng dẫn chi tiết trong [aws_deploy_guide.md](aws_deploy_guide.md)

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `MODE` | Mode: `BACKFILL`, `HOURLY`, hoặc `COMPACTION` | Yes | `HOURLY` |
| `VISUAL_CROSSING_API_KEY` | Visual Crossing API key | Yes (BACKFILL, HOURLY) | - |
| `ELECTRICITY_MAPS_API_KEY` | Electricity Maps API key | Yes (BACKFILL, HOURLY) | - |
| `S3_BUCKET` | S3 bucket name | Yes | `vietnam-energy-data` |
| `LOG_LEVEL` | Logging level | No | `INFO` |

### Mode Comparison

| Mode | Purpose | Frequency | Data Collected | Output Files |
|------|---------|-----------|----------------|--------------|
| **BACKFILL** | Thu thập dữ liệu lịch sử | 1 lần | 2021 → hôm qua | `data.json` (1 file/ngày) |
| **HOURLY** | Thu thập dữ liệu real-time | Mỗi giờ | Giờ trước | `HH_30.json` (1 file/giờ) |
| **COMPACTION** | Gộp hourly files | 1 lần/ngày (01:00 AM) | Ngày hôm qua | `data.json` (gộp 24 files) |

---

## 📊 Output Data Structure

### S3 Path Structure

#### 1. HOURLY Mode (Real-time)

Mỗi giờ tạo 1 file riêng:

```
s3://vietnam-energy-data/
└── bronze/
    ├── weather/
    │   └── year=2024/
    │       └── month=01/
    │           └── day=11/
    │               ├── 00_30.json  # Data giờ 00:00
    │               ├── 01_30.json  # Data giờ 01:00
    │               ├── 02_30.json
    │               └── ...
    │               └── 23_30.json  # Data giờ 23:00
    │
    └── electricity/
        ├── carbon_intensity/
        │   └── year=2024/month=01/day=11/
        │       ├── 00_30.json
        │       ├── 01_30.json
        │       └── ...
        └── total_load/
            └── ...
```

#### 2. COMPACTION Mode (Daily cleanup)

Sau khi chạy compaction, 24 files trên được gộp thành:

```
s3://vietnam-energy-data/
└── bronze/
    ├── weather/
    │   └── year=2024/month=01/day=11/
    │       └── data.json  # ✅ Gộp từ 24 files HH_30.json
    │
    └── electricity/
        ├── carbon_intensity/
        │   └── year=2024/month=01/day=11/
        │       └── data.json  # ✅ Gộp từ 24 files
        └── ...
```

#### 3. BACKFILL Mode (Historical data)

Tạo luôn file `data.json` cho mỗi ngày:

```
s3://vietnam-energy-data/
└── bronze/
    ├── weather/
    │   ├── year=2021/month=10/day=27/data.json
    │   ├── year=2021/month=10/day=28/data.json
    │   └── ...
    └── electricity/
        └── ...
```

---

## 📋 Data Schema

### HOURLY Mode - Single Hour File (HH_30.json)

#### Weather (13_30.json)

```json
{
  "queryCost": 1,
  "latitude": 14.0583,
  "longitude": 108.2772,
  "resolvedAddress": "Vietnam",
  "timezone": "Asia/Bangkok",
  "days": [
    {
      "datetime": "2024-01-11",
      "hours": [
        {
          "datetime": "13:00:00",
          "temp": 25.5,
          "humidity": 75.2,
          "precip": 0.0,
          "windspeed": 12.5,
          "cloudcover": 45.0
        }
      ]
    }
  ]
}
```

#### Electricity (13_30.json)

```json
{
  "zone": "VN",
  "history": [
    {
      "datetime": "2024-01-11T13:00:00Z",
      "carbonIntensity": 450,
      "fossilFreePercentage": 35
    }
  ],
  "_metadata": {
    "signal": "carbon_intensity",
    "query_date": "2024-01-11",
    "hour": "13",
    "zone": "VN"
  }
}
```

### COMPACTED File (data.json)

#### Weather

```json
{
  "queryCost": 1,
  "latitude": 14.0583,
  "longitude": 108.2772,
  "days": [
    {
      "datetime": "2024-01-11",
      "hours": [
        {"datetime": "00:00:00", "temp": 24.0, ...},
        {"datetime": "01:00:00", "temp": 24.5, ...},
        ...
        {"datetime": "23:00:00", "temp": 26.0, ...}
      ]
    }
  ]
}
```

#### Electricity

```json
{
  "zone": "VN",
  "history": [
    {"datetime": "2024-01-11T00:00:00Z", "carbonIntensity": 450, ...},
    {"datetime": "2024-01-11T01:00:00Z", "carbonIntensity": 455, ...},
    ...
    {"datetime": "2024-01-11T23:00:00Z", "carbonIntensity": 460, ...}
  ],
  "_metadata": {
    "signal": "carbon_intensity",
    "query_date": "2024-01-11",
    "zone": "VN"
  }
}
```

---

## 🔍 Monitoring & Logging

### CloudWatch Logs

Logs được ghi vào: `/ecs/vietnam-energy-ingestion`

### Log Examples

#### HOURLY Mode

```
☀️ Starting weather data ingestion (HOURLY) for 2024-01-11 13:00
🎯 Target: 2024-01-11 13:00
✅ 2024-01-11 13:00 -> s3://.../13_30.json
```

#### COMPACTION Mode

```
🗜️ Starting full compaction for 2024-01-10
📁 Found 24 hourly files
✅ Compacted 24 hours -> s3://.../data.json
🗑️ Deleted 24/24 hourly files
```

---

## 🕐 Scheduling Strategy

### AWS EventBridge Schedules

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  SCHEDULE 1: HOURLY INGESTION                      │
│  ─────────────────────────────                     │
│  Cron: 30 * * * ? *                                │
│  (Chạy phút 30 mỗi giờ)                            │
│  Mode: HOURLY                                       │
│  → Lấy dữ liệu của giờ trước                       │
│                                                     │
│  Example:                                           │
│  - 01:30 → Lấy data 00:00                          │
│  - 02:30 → Lấy data 01:00                          │
│  - 13:30 → Lấy data 12:00                          │
│                                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                                                     │
│  SCHEDULE 2: DAILY COMPACTION                      │
│  ─────────────────────────────                     │
│  Cron: 0 18 * * ? *                                │
│  (01:00 AM Vietnam = 18:00 UTC)                    │
│  Mode: COMPACTION                                   │
│  → Gộp 24 files của ngày hôm qua                   │
│                                                     │
│  Example:                                           │
│  - 2024-01-11 01:00 → Compact dữ liệu 2024-01-10  │
│    (Gộp 00_30.json → 23_30.json thành data.json)  │
│                                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                                                     │
│  MANUAL TASK: BACKFILL                             │
│  ──────────────────────                            │
│  Mode: BACKFILL                                     │
│  → Chạy 1 lần để lấy dữ liệu lịch sử              │
│  → Tạo file data.json trực tiếp (không qua hourly) │
│                                                     │
└─────────────────────────────────────────────────────┘
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

### Manual Test - HOURLY Mode

```bash
# Test Weather API (lấy giờ 13:00)
python -c "
from src.api_clients.weather import WeatherAPIClient
from src.config import Config

client = WeatherAPIClient(
    Config.VISUAL_CROSSING_API_KEY,
    Config.WEATHER_API_HOST,
    Config.WEATHER_LOCATION,
    Config.WEATHER_ELEMENTS
)

data = client.fetch_data('2024-01-11')
hour_13 = [h for h in data['days'][0]['hours'] if h['datetime'].startswith('13:')][0]
print(hour_13)
"
```

### Manual Test - COMPACTION

```bash
# Test compaction locally
MODE=COMPACTION python src/main.py
```

---

## 📈 Performance

| Mode | Duration | Cost/Month | API Calls |
|------|----------|-----------|-----------|
| **BACKFILL** | ~2-3 giờ (1 lần) | $0 (one-time) | ~4,000 calls |
| **HOURLY** | ~10-20 giây/lần | ~$2-3 | 6 calls/giờ × 720 giờ/tháng |
| **COMPACTION** | ~30-60 giây/ngày | ~$0.30 | 0 (chỉ đọc S3) |

**Total Cost**: ~$2-3/tháng

---

## 🐛 Troubleshooting

### Issue: HOURLY task fails "Hour not found"

**Nguyên nhân:** API chưa có dữ liệu cho giờ đó

**Solution:** Retry sau 30 phút hoặc skip

### Issue: COMPACTION finds < 24 files

**Nguyên nhân:** Một số HOURLY tasks failed

**Solution:** Check CloudWatch logs để xem giờ nào bị fail, rerun HOURLY cho giờ đó

### Issue: Duplicate files (both HH_30.json và data.json exist)

**Nguyên nhân:** COMPACTION chưa chạy hoặc failed

**Solution:** Manual chạy COMPACTION task

---

## 📝 Migration Guide (DAILY → HOURLY)

Nếu bạn đang có dữ liệu từ DAILY mode cũ:

1. **Dữ liệu cũ (data.json)**: Giữ nguyên, không conflict với HOURLY
2. **Chạy HOURLY**: Bắt đầu từ ngày hôm nay, tạo HH_30.json files
3. **Chạy COMPACTION**: Mỗi ngày gộp lại thành data.json

→ Kết quả: Cấu trúc dữ liệu giống hệt DAILY mode cũ!

---

## 🎯 Next Steps

1. ✅ **Test HOURLY mode** với 1 ngày
2. ✅ **Test COMPACTION** sau khi có đủ 24 hourly files
3. ✅ **Deploy lên ECS** với 2 EventBridge schedules
4. ✅ **Monitor logs** để đảm bảo không có gap trong dữ liệu

---

## 👥 Contributors

- **Your Name** - Initial work

---

## 📄 License

MIT License