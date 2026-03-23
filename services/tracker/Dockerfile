# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip hatch

# Copy soorma-common package first (small, stable)
# Build context should be soorma-core root
COPY libs/soorma-common /app/soorma-common/

# Build soorma-common
WORKDIR /app/soorma-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Copy soorma-service-common package
COPY libs/soorma-service-common /app/soorma-service-common/

# Build soorma-service-common
WORKDIR /app/soorma-service-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Copy soorma-nats package (shared NATS client for infrastructure services)
COPY libs/soorma-nats /app/soorma-nats/

# Build soorma-nats
WORKDIR /app/soorma-nats
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Copy tracker service (copy last so changes don't rebuild libs)
COPY services/tracker /app/tracker/

# Build tracker service
WORKDIR /app/tracker
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Download all dependencies as wheels (excluding the packages we just built)
# --find-links ensures locally-built wheels (soorma-common, soorma-service-common, soorma-nats) are used instead of PyPI
RUN pip wheel --wheel-dir /app/wheels --find-links /app/wheels . \
    && rm -f /app/wheels/soorma_common-*.whl /app/wheels/soorma_service_common-*.whl /app/wheels/soorma_nats-*.whl /app/wheels/tracker_service-*.whl

# Re-add our built packages (ensures we use local versions, not PyPI)
WORKDIR /app/soorma-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .
WORKDIR /app/soorma-service-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .
WORKDIR /app/soorma-nats
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
        /app/wheels/soorma_service_common-*.whl \
        /app/wheels/soorma_nats-*.whl \
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
