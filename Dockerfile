FROM python:3.10-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application files
COPY . .

# Create necessary directories
RUN mkdir -p logs signals data

# Environment
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=5m --timeout=3s \
    CMD python -c "import os; exit(0 if os.path.exists('logs/gold_analyzer.log') else 1)"

# Run
CMD ["python", "main_robust.py"]