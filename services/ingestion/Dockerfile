# 🐳 Dockerfile cho Service Ingestion
# Base image: Python 3.11 slim (nhẹ nhất có thể)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (nếu cần)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (để tận dụng Docker cache)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Set Python path
ENV PYTHONPATH=/app

# Set environment variables (sẽ được override bởi ECS Task Definition)
ENV MODE=DAILY
ENV LOG_LEVEL=INFO

# Health check (optional - để ECS biết container đã ready)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the application
CMD ["python", "src/main.py"]