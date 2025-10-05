FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY services/orchestrator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library
COPY shared /app/shared

# Copy service code
COPY services/orchestrator/app /app/app

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
