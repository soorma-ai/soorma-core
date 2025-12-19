# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip hatch

# Copy soorma-common package first
# Build context should be soorma-core root (i.e., soorma-platform/core/)
COPY libs/soorma-common /app/soorma-common/

# Copy registry service
COPY services/registry /app/registry/

# Build soorma-common
WORKDIR /app/soorma-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Build registry service
WORKDIR /app/registry
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app

# Copy wheels from builder
COPY --from=builder /app/wheels /app/wheels

# Install dependencies and the service
RUN pip install --no-cache-dir \
    fastapi>=0.104.0 \
    "uvicorn[standard]>=0.24.0" \
    "sqlalchemy[asyncio]>=2.0.0" \
    aiosqlite>=0.19.0 \
    asyncpg>=0.29.0 \
    psycopg2-binary>=2.9.0 \
    alembic>=1.12.0 \
    pydantic-settings>=2.0.0 \
    cachetools>=5.0.0 \
    && pip install --no-cache-dir /app/wheels/*.whl \
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
