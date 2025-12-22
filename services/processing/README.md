# 🔄 Service Processing - Vietnam Energy Forecasting

## 📋 Mô tả

Service Processing là thành phần thứ 2 trong pipeline, chịu trách nhiệm làm sạch dữ liệu và tạo features cho ML.

**Input**: Dữ liệu thô từ S3 Bronze Layer (Service Ingestion)  
**Output**: 
- S3 Silver Layer (Cleaned data)
- S3 Gold Layer (Feature store)

---

## 🏗️ Kiến trúc

```
Bronze (JSON)
    ↓
┌─────────────────────────┐
│  Weather Cleaner        │
│  - Parse JSON           │
│  - Convert timezone     │
│  - Handle missing       │
│  - Remove outliers      │
└───────────┬─────────────┘
            ↓
Silver (Parquet) ─────┐
                       │
┌─────────────────────────┐      ┌──────────────────────┐
│  Electricity Cleaner    │      │  Feature Engineer    │
│  - Parse 5 signals      │      │  - Time features     │
│  - Clean & merge        │  →   │  - Lag features      │
└───────────┬─────────────┘      │  - Rolling features  │
            ↓                     │  - Interactions      │
Silver (Parquet) ─────────────→  └─────────┬────────────┘
                                            ↓
                                 Gold (Parquet Features)
```

---

## 📁 Cấu trúc thư mục

```
services/processing/
│
├── Dockerfile                  # 🐳 Container definition
├── requirements.txt            # 📦 Dependencies
├── .env.example                # 🔑 Environment template
├── .dockerignore               # 🛡️ Exclude files
│
└── src/                        # 🧠 Source code
    ├── __init__.py
    ├── main.py                 # 🏁 Main orchestrator
    ├── config.py               # ⚙️ Configuration
    ├── s3_connector.py         # 🔌 S3 read/write
    │
    └── etl/                    # 🔄 ETL logic
        ├── __init__.py
        ├── weather_cleaner.py      # ☀️ Clean weather data
        ├── electricity_cleaner.py  # ⚡ Clean electricity data
        └── feature_eng.py          # ⚙️ Feature engineering
```

---

## 🚀 Quick Start

### 1. Local Development

```bash
cd services/processing
pip install -r requirements.txt

# Copy và config environment
cp .env.example .env
# Edit .env với S3 bucket name

# Chạy local (DAILY mode)
MODE=DAILY python src/main.py

# Chạy BACKFILL
MODE=BACKFILL python src/main.py
```

### 2. Docker Local Test

```bash
docker build -t vietnam-energy-processing:latest .

docker run --rm \
  -e MODE=DAILY \
  -e S3_BUCKET=vietnam-energy-data \
  -e AWS_ACCESS_KEY_ID=your_id \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  vietnam-energy-processing:latest
```

### 3. AWS Deployment

Xem [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md)

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `MODE` | `BACKFILL` hoặc `DAILY` | Yes | `DAILY` |
| `S3_BUCKET` | S3 bucket name | Yes | `vietnam-energy-data` |
| `LOG_LEVEL` | Logging level | No | `INFO` |

### Processing Config

File `config.py` chứa các config:

```python
# Data paths
BRONZE_PREFIX = "bronze"
SILVER_PREFIX = "silver"
GOLD_PREFIX = "gold"

# Feature engineering
LAG_HOURS = [1, 2, 3, 6, 12, 24]
ROLLING_WINDOWS = [3, 6, 12, 24]

# Data quality
MAX_MISSING_RATIO = 0.3  # 30%
OUTLIER_ZSCORE_THRESHOLD = 3.5
```

---

## 📊 Data Flow

### Bronze → Silver (Cleaning)

**Weather Data:**
```json
// Bronze (JSON)
{
  "days": [{
    "hours": [
      {"datetime": "00:00:00", "temp": 24.0, ...}
    ]
  }]
}
```

↓ **Cleaning steps:**
1. Parse JSON structure
2. Convert UTC → UTC+7 (Vietnam timezone)
3. Handle missing values (forward fill)
4. Remove outliers (Z-score)
5. Standardize column names

```python
# Silver (Parquet)
datetime            | temperature | humidity | precipitation | wind_speed | cloud_cover
2024-12-20 00:00:00 | 24.0       | 78.0     | 0.0          | 12.5       | 45.0
2024-12-20 01:00:00 | 23.8       | 79.5     | 0.0          | 11.8       | 50.2
```

**Electricity Data:**
- Process 5 signals riêng biệt
- Merge lại thành 1 DataFrame
- Fill missing values

### Silver → Gold (Feature Engineering)

**Features được tạo:**

1. **Time-based** (13 features)
   - `hour`, `day_of_week`, `month`, `quarter`, `year`
   - `is_weekend`, `is_holiday`
   - Cyclical encoding: `hour_sin`, `hour_cos`, etc.

2. **Lag features** (18 features với 6 lags × 3 columns)
   - `temperature_lag_1`, `temperature_lag_2`, ...
   - `humidity_lag_1`, `humidity_lag_2`, ...

3. **Rolling features** (32 features với 4 windows × 4 columns × 2 stats)
   - `temperature_rolling_mean_3`, `temperature_rolling_std_3`
   - `humidity_rolling_mean_6`, etc.

4. **Interaction features** (3 features)
   - `heat_index` = temperature × humidity
   - `wind_chill` = temperature - wind_speed × 0.5
   - `rain_indicator` = (precipitation > 0) & (humidity > 80)

**Total: ~66 features**

---

## 🔄 Execution Modes

### DAILY Mode
- **Trigger**: EventBridge khi có Bronze data mới
- **Input**: Bronze data của ngày hôm qua
- **Output**: Silver + Gold cho ngày đó
- **Duration**: 2-5 phút

### BACKFILL Mode
- **Trigger**: Manual (ECS Console)
- **Input**: Tất cả Bronze data hiện có
- **Output**: Silver + Gold cho tất cả ngày
- **Duration**: 20-40 phút (tùy số ngày)

---

## 🎯 Data Quality

### Cleaning Rules

**Weather:**
- Temperature: 15-40°C (Vietnam range)
- Humidity: 30-100%
- Wind speed: 0-50 km/h
- Outliers: Z-score > 3.5

**Electricity:**
- Forward fill missing values
- Merge multiple signals
- Handle empty responses

### Validation

```python
# Sau cleaning
assert df['temperature'].between(15, 40).all()
assert df['datetime'].is_monotonic_increasing
assert df.isnull().sum().sum() == 0  # No missing values
```

---

## 📈 Performance

- **Throughput**: ~1000 rows/second (cleaning)
- **Memory**: <1 GB RAM (DAILY mode)
- **CPU**: 0.5 vCPU đủ cho DAILY
- **Storage**: 
  - Silver: ~30 MB/tháng (Parquet với compression)
  - Gold: ~50 MB/tháng

---

## 🐛 Troubleshooting

### Issue: "No Bronze data found"

**Nguyên nhân**: Ingestion chưa chạy hoặc path sai

**Fix:**
```bash
# Check Bronze data
aws s3 ls s3://vietnam-energy-data/bronze/weather/ --recursive

# Verify path trong config
echo $S3_BUCKET
```

---

### Issue: Memory error (OOM)

**Nguyên nhân**: Processing quá nhiều data

**Fix:**
- Tăng memory trong Task Definition (1 GB → 2 GB)
- Hoặc giảm `BACKFILL_CHUNK_DAYS` trong config

---

### Issue: Too many NaN in features

**Nguyên nhân**: Lag/rolling features cần historical data

**Fix:** 
- Normal behavior: Các rows đầu sẽ có NaN (do lag)
- Sẽ bị drop tự động trong `dropna()`
- Cần ít nhất 24 giờ data để có đầy đủ features

---

## 📊 Monitoring

### CloudWatch Logs

```bash
# Xem logs realtime
aws logs tail /ecs/vietnam-energy-processing --follow

# Filter errors
aws logs filter-log-events \
  --log-group-name /ecs/vietnam-energy-processing \
  --filter-pattern "ERROR"
```

### Key Metrics

1. **Processing Duration**: Bao lâu để xử lý 1 ngày
2. **Success Rate**: % task thành công
3. **Data Volume**: Số rows sau cleaning
4. **Feature Count**: Số features được tạo

### Sample Log Output

```
⚙️ Starting feature engineering...
  → Merged datasets: 24 rows
  → Created time features
  → Created lag features
  → Created rolling features
  → Created cyclical features
  → Created holiday features
  → Created interaction features
  → Dropped 24 rows with NaN
✅ Feature engineering complete: 0 rows, 66 features
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

### Manual Test với Sample Data

```python
from etl.weather_cleaner import WeatherCleaner

cleaner = WeatherCleaner()
sample_data = {...}  # Sample Bronze JSON
cleaned_df = cleaner.clean(sample_data, "2024-12-20")
print(cleaned_df.head())
```

---

## 📝 TODO

- [ ] Add data quality metrics tracking
- [ ] Implement alerting khi data quality thấp
- [ ] Add more interaction features
- [ ] Optimize memory usage cho large backfills
- [ ] Add unit tests

---

## 🔗 Related Services

- **Service Ingestion** (Upstream): Thu thập Bronze data
- **Service Training** (Downstream): Train ML model từ Gold features
- **Service Dashboard** (Downstream): Visualize predictions

---

## 💰 Cost Estimate

- **ECS Fargate**: ~$0.50/month (10 min/day @ 0.5 vCPU)
- **S3 Storage**: ~$0.70/month (30 GB Silver + Gold)
- **CloudWatch Logs**: ~$1.00/month
- **Total**: ~$2-3/month

---

## 📞 Support

**Logs**: CloudWatch → `/ecs/vietnam-energy-processing`

**Common Issues**:
- No Bronze data → Check Ingestion service
- Memory error → Increase memory or use chunking
- Too many NaN → Normal for first rows (lag features)

---

## 📄 License

MIT License