FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/context/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library
COPY shared/ /app/shared/

# Copy service code
COPY services/context/app/ /app/app/

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8002/health')"

# Run the service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]