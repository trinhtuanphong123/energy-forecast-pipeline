# 📝 TÓM TẮT THAY ĐỔI CODE - SERVICE INGESTION

## 🎯 Mục tiêu

Thay đổi từ **DAILY mode** (1 lần/ngày, 1 file/ngày) sang:
- **HOURLY mode** (24 lần/ngày, 24 files/ngày)
- **COMPACTION mode** (1 lần/ngày, gộp 24 files → 1 file)
- **BACKFILL mode** (giữ nguyên)

---

## 📂 DANH SÁCH FILES

### ✅ FILES CẦN SỬA (4 files)

| File | Thay đổi | Lý do |
|------|---------|-------|
| `src/config.py` | **Sửa toàn bộ** | Thêm mode HOURLY, COMPACTION; thay đổi date range logic |
| `src/s3_writer.py` | **Sửa toàn bộ** | Thêm hỗ trợ hourly files (HH_30.json); thêm methods list/read/delete files |
| `src/main.py` | **Viết lại hoàn toàn** | Tách thành 3 workflows riêng cho 3 modes |
| `README.md` | **Viết lại hoàn toàn** | Cập nhật documentation cho 3 modes |

### ➕ FILES MỚI (2 files)

| File | Nội dung |
|------|---------|
| `src/compactor.py` | **NEW** - Logic gộp hourly files thành daily file |
| `aws_deploy_guide.md` | **CẬP NHẬT** - Hướng dẫn deploy với 2 EventBridge schedules |

### 🔵 FILES GIỮ NGUYÊN (6 files)

| File | Trạng thái |
|------|-----------|
| `src/api_clients/base.py` | ✅ Không thay đổi |
| `src/api_clients/weather.py` | ✅ Không thay đổi |
| `src/api_clients/electricity.py` | ✅ Không thay đổi |
| `src/api_clients/__init__.py` | ✅ Không thay đổi |
| `src/__init__.py` | ✅ Không thay đổi |
| `requirements.txt` | ✅ Không thay đổi |
| `Dockerfile` | ✅ Không thay đổi |
| `.gitignore` | ✅ Không thay đổi |

---

## 🔧 CHI TIẾT THAY ĐỔI

### 1. `src/config.py`

**Thay đổi chính:**

```python
# CŨ
MODE = "DAILY" hoặc "BACKFILL"

# MỚI
MODE = "BACKFILL" | "HOURLY" | "COMPACTION"
```

**Thêm methods:**
- `get_target_datetime()` - Trả về (date, hour) cho HOURLY mode
- Cập nhật `get_date_range()` - Xử lý 3 modes khác nhau
- Cập nhật `validate()` - Không cần API keys cho COMPACTION mode

**Ví dụ:**

```python
# BACKFILL: start_date=2021-10-27, end_date=yesterday
# HOURLY: target_date=today, target_hour=previous_hour
# COMPACTION: start_date=yesterday, end_date=yesterday
```

---

### 2. `src/s3_writer.py`

**Thay đổi chính:**

**Signature methods thay đổi:**

```python
# CŨ
def _generate_partition_path(data_source, query_date, signal_name=None)
def write_weather_data(data, query_date)

# MỚI
def _generate_partition_path(data_source, query_date, signal_name=None, hour=None)
def write_weather_data(data, query_date, hour=None)
```

**Output path:**

```python
# hour=None (compacted/backfill)
"bronze/weather/year=2024/month=01/day=11/data.json"

# hour="13" (hourly)
"bronze/weather/year=2024/month=01/day=11/13_30.json"
```

**Thêm methods mới:**

```python
def list_hourly_files(data_source, query_date, signal_name=None)
    # → Trả về list các HH_30.json files

def read_json(s3_key)
    # → Đọc JSON từ S3

def delete_file(s3_key)
    # → Xóa file trên S3
```

---

### 3. `src/compactor.py` (FILE MỚI)

**Class:** `DataCompactor`

**Methods:**

```python
def compact_weather_data(query_date)
    # Input: 24 files HH_30.json
    # Output: 1 file data.json
    # Steps:
    #   1. List all hourly files
    #   2. Read each file
    #   3. Extract hour data
    #   4. Merge all hours
    #   5. Write compacted file
    #   6. Delete hourly files

def compact_electricity_data(query_date, signal_name)
    # Tương tự weather

def compact_all(query_date)
    # Compact cả weather + all electricity signals
```

**Workflow:**

```
Input (24 files):
  00_30.json → {hours: [{datetime: "00:00:00", temp: 24.0}]}
  01_30.json → {hours: [{datetime: "01:00:00", temp: 24.5}]}
  ...
  23_30.json → {hours: [{datetime: "23:00:00", temp: 26.0}]}

Output (1 file):
  data.json → {
    days: [{
      datetime: "2024-01-11",
      hours: [
        {datetime: "00:00:00", temp: 24.0},
        {datetime: "01:00:00", temp: 24.5},
        ...
        {datetime: "23:00:00", temp: 26.0}
      ]
    }]
  }
```

---

### 4. `src/main.py`

**Thay đổi lớn: Tách thành 3 workflows riêng**

**CŨ (1 workflow):**

```python
def main():
    if MODE == "BACKFILL":
        # Lấy toàn bộ ngày, mỗi ngày 1 file
    else:  # DAILY
        # Lấy hôm qua, 1 file
```

**MỚI (3 workflows):**

```python
def run_backfill_mode():
    # Lấy toàn bộ ngày từ 2021 đến hiện tại
    # Mỗi ngày → 1 file data.json
    ingest_weather_data_backfill(...)
    ingest_electricity_data_backfill(...)

def run_hourly_mode():
    # Lấy 1 giờ cụ thể
    # 1 giờ → 1 file HH_30.json
    target_date, target_hour = Config.get_target_datetime()
    ingest_weather_data_hourly(target_date, target_hour)
    ingest_electricity_data_hourly(target_date, target_hour)

def run_compaction_mode():
    # Gộp 24 files của ngày hôm qua
    # 24 files HH_30.json → 1 file data.json
    compactor.compact_all(yesterday)

def main():
    mode = Config.get_mode()
    if mode == "BACKFILL":
        run_backfill_mode()
    elif mode == "HOURLY":
        run_hourly_mode()
    elif mode == "COMPACTION":
        run_compaction_mode()
```

**Thêm functions:**

```python
def ingest_weather_data_backfill(...)  # Lấy full day → data.json
def ingest_weather_data_hourly(...)    # Lấy 1 hour → HH_30.json

def ingest_electricity_data_backfill(...)  # Lấy full day
def ingest_electricity_data_hourly(...)    # Lấy 1 hour
```

**Logic extract 1 hour từ full day response:**

```python
# API trả về full day data
data = weather_client.fetch_data("2024-01-11")

# Extract chỉ giờ 13:00
target_hour_data = None
for hour_data in data['days'][0]['hours']:
    if hour_data['datetime'] == "13:00:00":
        target_hour_data = hour_data
        break

# Save single hour
hourly_data = {
    'days': [{
        'datetime': "2024-01-11",
        'hours': [target_hour_data]  # Chỉ 1 hour
    }]
}

s3_writer.write_weather_data(hourly_data, "2024-01-11", hour="13")
```

---

## 🔄 WORKFLOW SO SÁNH

### CŨ (DAILY MODE)

```
Day 1 (DAILY task)
  ↓
Lấy toàn bộ 24h của ngày hôm qua
  ↓
Lưu: bronze/weather/year=2024/month=01/day=10/data.json
      ↑ 1 file với 24 điểm dữ liệu
```

### MỚI (HOURLY + COMPACTION)

```
Day 1 - 00:30 (HOURLY task #1)
  ↓
Lấy data giờ 00:00
  ↓
Lưu: .../day=11/00_30.json (1 điểm)

Day 1 - 01:30 (HOURLY task #2)
  ↓
Lấy data giờ 01:00
  ↓
Lưu: .../day=11/01_30.json (1 điểm)

... (tiếp tục 22 lần nữa)

Day 1 - 23:30 (HOURLY task #24)
  ↓
Lấy data giờ 23:00
  ↓
Lưu: .../day=11/23_30.json (1 điểm)

Day 2 - 01:00 (COMPACTION task)
  ↓
Đọc 24 files: 00_30.json → 23_30.json
  ↓
Gộp thành 1 file: data.json (24 điểm)
  ↓
Xóa 24 files hourly
  ↓
Kết quả: .../day=11/data.json ← Giống hệt DAILY cũ!
```

---

## 📊 OUTPUT DATA STRUCTURE

### S3 Structure Evolution

**Trong ngày hôm nay (đang thu thập):**

```
bronze/weather/year=2024/month=01/day=11/
├── 00_30.json  ✅ (Collected at 00:30)
├── 01_30.json  ✅ (Collected at 01:30)
├── 02_30.json  ✅ (Collected at 02:30)
└── ... (up to 23_30.json)
```

**Sau khi compaction (ngày hôm qua):**

```
bronze/weather/year=2024/month=01/day=10/
└── data.json  ✅ (Compacted at Day 11 01:00)
```

→ **Kết quả cuối cùng giống hệt DAILY mode cũ!**

---

## 🎯 DEPLOYMENT CHANGES

### CŨ (1 EventBridge Schedule)

```
Schedule: vietnam-energy-daily-ingestion
Cron: 0 18 * * ? *  (01:00 AM Vietnam)
Mode: DAILY
```

### MỚI (2 EventBridge Schedules)

```
Schedule 1: vietnam-energy-hourly-ingestion
Cron: 30 * * * ? *  (Every hour at :30)
Mode: HOURLY

Schedule 2: vietnam-energy-daily-compaction
Cron: 0 18 * * ? *  (01:00 AM Vietnam)
Mode: COMPACTION
```

---

## ✅ CHECKLIST TESTING

### Test BACKFILL (Manual)

- [ ] Chạy với `MODE=BACKFILL`
- [ ] Kiểm tra có file `data.json` cho mỗi ngày
- [ ] Mỗi file có 24 điểm dữ liệu

### Test HOURLY (Schedule)

- [ ] Schedule chạy đúng giờ (mỗi giờ phút 30)
- [ ] Mỗi lần chạy tạo 1 file `HH_30.json`
- [ ] File có 1 điểm dữ liệu đúng giờ

### Test COMPACTION (Schedule)

- [ ] Schedule chạy đúng giờ (01:00 AM)
- [ ] List được 24 files hourly
- [ ] Gộp thành 1 file `data.json`
- [ ] File có 24 điểm dữ liệu (sorted by time)
- [ ] 24 files hourly đã bị xóa

### Test Integration

- [ ] Sau 1 tuần, mỗi ngày có đúng 1 file `data.json`
- [ ] Không có gap trong dữ liệu
- [ ] Không có file hourly bị orphan

---

## 📌 NOTES

### Tại sao cần HOURLY + COMPACTION thay vì DAILY?

**Lý do:**

1. **Real-time data access**: Có thể dùng dữ liệu trong ngày cho predictions
2. **Fault tolerance**: Nếu 1 giờ fail, chỉ mất 1 điểm thay vì cả ngày
3. **Incremental updates**: Không cần chờ đến cuối ngày mới có dữ liệu
4. **Backward compatibility**: Sau compaction, cấu trúc giống hệt DAILY cũ

### Tại sao không lưu trực tiếp thành data.json?

**Vì:**

- API có thể trả về data với delay
- Nếu lưu trực tiếp data.json, phải overwrite file liên tục (risky)
- Với hourly files, mỗi giờ là 1 file độc lập, không conflict

### Migration từ DAILY sang HOURLY

**Dữ liệu cũ (DAILY):**
```
bronze/weather/year=2024/month=01/day=01/data.json
bronze/weather/year=2024/month=01/day=02/data.json
...
bronze/weather/year=2024/month=01/day=10/data.json
```

**Dữ liệu mới (HOURLY):**
```
bronze/weather/year=2024/month=01/day=11/
├── 00_30.json
├── 01_30.json
...
```

**Sau compaction:**
```
bronze/weather/year=2024/month=01/day=11/data.json  ← Giống DAILY!
```

→ **Không conflict, có thể dùng chung pipeline!**

---

## 🚀 DEPLOYMENT STEPS

1. ✅ Update code (6 files: config, s3_writer, main, compactor, README, aws_deploy_guide)
2. ✅ Build & push Docker image mới
3. ✅ Update Task Definition (MODE=HOURLY)
4. ✅ Xóa schedule cũ: `vietnam-energy-daily-ingestion`
5. ✅ Tạo schedule mới: `vietnam-energy-hourly-ingestion`
6. ✅ Tạo schedule mới: `vietnam-energy-daily-compaction`
7. ✅ Monitor logs trong 24h đầu
8. ✅ Verify dữ liệu sau compaction

---

Bạn có câu hỏi gì về changes này không? 🚀