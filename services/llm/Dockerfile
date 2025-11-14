FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY services/llm/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library
COPY shared/ /app/shared/

# Copy service code
COPY services/llm/app/ /app/app/

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8003/health')"

# Run the service (use PORT env var or default to 8003)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8003}