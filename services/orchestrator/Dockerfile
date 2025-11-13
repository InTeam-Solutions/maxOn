FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY services/orchestrator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library
COPY shared /app/shared

# Copy service code
COPY services/orchestrator/app /app/app

# Copy entrypoint script
COPY services/orchestrator/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose port (default 8001, but can be overridden by $PORT env var)
EXPOSE 8001

# Run the service (Railway will inject $PORT)
ENTRYPOINT ["/app/entrypoint.sh"]
