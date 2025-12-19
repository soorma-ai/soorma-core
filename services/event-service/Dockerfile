# Event Service Dockerfile
# Multi-stage build for minimal image size
# Build context should be soorma-core root (i.e., soorma-platform/core/)

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir pip --upgrade

# Copy project files from services/event-service/
COPY services/event-service/pyproject.toml services/event-service/README.md ./
COPY services/event-service/src/ ./src/

# Install dependencies
RUN pip install --no-cache-dir .


FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY services/event-service/src/ ./src/

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8082/health')"

# Run the service
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8082"]
