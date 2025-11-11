FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/worker/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code
COPY shared /app/shared

# Copy core models (needed for database queries)
COPY services/core/app/models /app/core_models

# Copy worker service code
COPY services/worker/app /app/app

# Run the worker
CMD ["python", "-u", "app/main.py"]
