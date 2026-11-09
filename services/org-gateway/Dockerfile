# SPDX-License-Identifier: FSL-1.1-ALv2
#
# S1 org-gateway (Infrastructure Design §2; D-ID-OI-09; D-CG-OI-10).
# Build from the repository root:
#   docker build -f services/org-gateway/Dockerfile -t soorma/org-gateway .
#
# - Both images pinned by digest, each the newest past the 7-day cooldown:
#     node:26.13.0, pushed 2026-10-29 (docker-library/repo-info 7d6f332)
#     distroless nodejs26-debian13:nonroot, uploaded 2026-10-31
# - Explicit COPY paths only; .dockerignore keeps out everything else,
#   deploy/local/.secrets/ above all
# - pnpm deploy --prod: the service and its production dependencies only
# - No shell, no package manager, a non-root user at run time
# - Three entry points: dist/main.js (S1), dist/migrate.js (org-migrate),
#   dist/healthcheck.js (the Compose healthcheck)

FROM node:26.13.0@sha256:6d2c7d5d074bf72f81ddc252b4fbb5d625bc028eeda49cb4b8c2ff8eda1ee617 AS build
WORKDIR /src
RUN npm install --global --ignore-scripts pnpm@12.18.0

# The workspace manifests and lockfile, for a frozen install.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json tsconfig.build.json ./
COPY tools/package.json tools/package.json
COPY deploy/package.json deploy/package.json
COPY contract/package.json contract/tsconfig.json contract/tsconfig.build.json contract/LICENSE contract/
COPY seams/LICENSE seams/LICENSE
COPY seams/identity-resolution/package.json seams/identity-resolution/tsconfig.json seams/identity-resolution/tsconfig.build.json seams/identity-resolution/
COPY packages/config/package.json packages/config/tsconfig.json packages/config/tsconfig.build.json packages/config/
COPY packages/org-identity/package.json packages/org-identity/tsconfig.json packages/org-identity/tsconfig.build.json packages/org-identity/
COPY packages/abuse-bound/package.json packages/abuse-bound/tsconfig.json packages/abuse-bound/tsconfig.build.json packages/abuse-bound/
COPY packages/identity-resolution/package.json packages/identity-resolution/tsconfig.json packages/identity-resolution/tsconfig.build.json packages/identity-resolution/
COPY packages/perimeter/package.json packages/perimeter/tsconfig.json packages/perimeter/tsconfig.build.json packages/perimeter/
COPY services/org-gateway/package.json services/org-gateway/tsconfig.json services/org-gateway/tsconfig.build.json services/org-gateway/
RUN pnpm install --frozen-lockfile

# The sources the build compiles, and the files the image serves.
COPY contract/generated/ contract/generated/
COPY contract/conventions/components.openapi.yaml contract/conventions/
COPY contract/org-gateway.openapi.yaml contract/envelope.schema.json contract/delivery.schema.json contract/
COPY seams/identity-resolution/src/ seams/identity-resolution/src/
COPY packages/config/src/ packages/config/src/
COPY packages/config/schema/ packages/config/schema/
COPY packages/org-identity/src/ packages/org-identity/src/
COPY packages/org-identity/migrations/ packages/org-identity/migrations/
COPY packages/abuse-bound/src/ packages/abuse-bound/src/
COPY packages/identity-resolution/src/ packages/identity-resolution/src/
COPY packages/perimeter/src/ packages/perimeter/src/
COPY services/org-gateway/src/ services/org-gateway/src/
RUN pnpm exec tsc -b services/org-gateway/tsconfig.build.json \
 && pnpm --filter @soorma/org-gateway deploy --prod --legacy /out

FROM gcr.io/distroless/nodejs26-debian13:nonroot@sha256:9b945e92c1b5463a4b75f11e8417515e4bea7355f6adfd79ec220fbbe905dda8
WORKDIR /app
COPY --from=build /out/ /app/
COPY data/breached/top-1m.sha256-64.bin data/breached/MANIFEST.md /app/data/breached/
ENV NODE_ENV=production \
    SOORMA_CONFIG=/etc/soorma/tenancy.yaml \
    SOORMA_BREACHED_DIR=/app/data/breached
USER nonroot
EXPOSE 8443 9443
CMD ["dist/main.js"]
