# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip hatch

# Copy and build shared packages
# Build context should be soorma-core root
COPY libs/soorma-common /app/soorma-common/
WORKDIR /app/soorma-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .

COPY libs/soorma-service-common /app/soorma-service-common/
WORKDIR /app/soorma-service-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Copy and build event service package
COPY services/event-service /app/event-service/
WORKDIR /app/event-service
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Build dependency wheels using local shared wheels via --find-links
RUN pip wheel --wheel-dir /app/wheels --find-links /app/wheels . \
    && rm -f /app/wheels/soorma_common-*.whl /app/wheels/soorma_service_common-*.whl /app/wheels/soorma_event_service-*.whl

# Re-add local packages to ensure local versions are used
WORKDIR /app/soorma-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .
WORKDIR /app/soorma-service-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .
WORKDIR /app/event-service
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app

# Copy wheels from builder
COPY --from=builder /app/wheels /app/wheels

# Install all wheels (packages + dependencies)
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --no-index --find-links=/app/wheels \
        /app/wheels/soorma_common-*.whl \
        /app/wheels/soorma_service_common-*.whl \
        /app/wheels/soorma_event_service-*.whl \
    && rm -rf /app/wheels

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8082/health').read()"

# Run the service
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8082"]
