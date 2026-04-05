# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip hatch

# Copy shared packages and identity-service source
COPY libs/soorma-common /app/soorma-common/
COPY libs/soorma-service-common /app/soorma-service-common/
COPY services/identity-service /app/identity-service/

# Build project wheels
WORKDIR /app/soorma-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .

WORKDIR /app/soorma-service-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .

WORKDIR /app/identity-service
RUN pip wheel --no-deps --wheel-dir /app/wheels .

# Download dependency wheels using locally-built packages
RUN pip wheel --wheel-dir /app/wheels --find-links /app/wheels . \
	&& rm -f /app/wheels/soorma_common-*.whl /app/wheels/soorma_service_common-*.whl /app/wheels/identity_service-*.whl

# Re-add local wheels to ensure local package versions are used
WORKDIR /app/soorma-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .

WORKDIR /app/soorma-service-common
RUN pip wheel --no-deps --wheel-dir /app/wheels .

WORKDIR /app/identity-service
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
	&& pip install --no-cache-dir --no-index --find-links=/app/wheels /app/wheels/soorma_common-*.whl /app/wheels/soorma_service_common-*.whl /app/wheels/identity_service-*.whl \
	&& rm -rf /app/wheels

# Copy migration config and entrypoint
COPY --chown=appuser:appuser --from=builder /app/identity-service/alembic.ini /app/
COPY --chown=appuser:appuser --from=builder /app/identity-service/alembic /app/alembic/
COPY --chown=appuser:appuser services/identity-service/entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8085

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8085/health').read()"

ENTRYPOINT ["/app/entrypoint.sh"]
