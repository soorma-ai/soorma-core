# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip hatch

# Copy soorma-common package first
# Build context should be soorma-core root
COPY libs/soorma-common /app/soorma-common/

# Copy SDK (needed for event bus subscription)
COPY sdk/python /app/sdk/

# Copy tracker service
COPY services/tracker /app/tracker/

# Build soorma-common
WORKDIR /app/soorma-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Build SDK
WORKDIR /app/sdk
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Build tracker service
WORKDIR /app/tracker
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Download all dependencies as wheels (excluding the packages we just built)
RUN pip wheel --wheel-dir /app/wheels . \
    && rm -f /app/wheels/soorma_common-*.whl /app/wheels/soorma_sdk-*.whl /app/wheels/tracker_service-*.whl

# Re-add our built packages (ensures we use local versions, not PyPI)
WORKDIR /app/soorma-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .
WORKDIR /app/sdk
RUN pip wheel --no-deps --wheel-dir /app/wheels .
WORKDIR /app/tracker
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
        /app/wheels/soorma_sdk-*.whl \
        /app/wheels/tracker_service-*.whl \
    && rm -rf /app/wheels

# Copy alembic config and migrations for database setup
COPY services/tracker/alembic.ini /app/alembic.ini
COPY services/tracker/alembic /app/alembic
COPY services/tracker/entrypoint.sh /app/entrypoint.sh

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8084

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8084/health').read()"

# Run entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
