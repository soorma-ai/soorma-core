# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip hatch

# Copy soorma-common package first
# Build context should be soorma-core root (i.e., soorma-platform/core/)
COPY libs/soorma-common /app/soorma-common/

# Copy registry service
COPY services/registry /app/registry/

# Build soorma-common (no deps, just the package)
WORKDIR /app/soorma-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Build registry service (no deps, just the package)
WORKDIR /app/registry
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Download all dependencies as wheels (excluding the packages we just built)
RUN pip wheel --wheel-dir /app/wheels . \
    && rm -f /app/wheels/soorma_common-*.whl /app/wheels/registry_service-*.whl

# Re-add our built packages (ensures we use local versions, not PyPI)
WORKDIR /app/soorma-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .
WORKDIR /app/registry
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
    && pip install --no-cache-dir --no-index --find-links=/app/wheels /app/wheels/soorma_common-*.whl /app/wheels/registry_service-*.whl \
    && rm -rf /app/wheels

# Copy alembic config and migrations for database setup
COPY --chown=appuser:appuser --from=builder /app/registry/alembic.ini /app/
COPY --chown=appuser:appuser --from=builder /app/registry/alembic /app/alembic/

# Copy entrypoint script
COPY --chown=appuser:appuser services/registry/entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the service via entrypoint to handle migrations
CMD ["/app/entrypoint.sh"]
