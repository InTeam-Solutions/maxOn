FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY services/api-gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library
COPY shared /app/shared

# Copy service code
COPY services/api-gateway/app /app/app

# Run
CMD ["python", "-m", "app.main"]
