# SPDX-License-Identifier: FSL-1.1-ALv2
#
# S4 event-ingest (U7 Infrastructure Design; D-ID-ET-01). Build from the
# repository root:
#   docker build -f services/event-ingest/Dockerfile -t soorma/event-ingest .
#
# - Both images pinned by digest, the same as S1's to S3's. The runtime image
#   is the one S4's JSON.rawJSON self-check was run in at NFR Design; S4
#   runs the same check at every start, and refuses to start without it
# - Explicit COPY paths only, for exactly S4's production closure;
#   .dockerignore keeps out everything else, deploy/local/.secrets/ above all
# - pnpm deploy --prod: the service and its production dependencies only.
#   The image holds no @soorma/org-identity, @soorma/identity-resolution,
#   @soorma/agent-identity, or @soorma/abuse-bound (TC-ET-083; D-ET-23)
# - No migrations: env-store's migrations/ is never copied, so none can ship.
#   {env}-migrate (S2's image) applies 0005 and 0006

FROM node:26.13.0@sha256:6d2c7d5d074bf72f81ddc252b4fbb5d625bc028eeda49cb4b8c2ff8eda1ee617 AS build
WORKDIR /src
RUN npm install --global --ignore-scripts pnpm@12.18.0
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json tsconfig.build.json ./
COPY tools/package.json tools/package.json
COPY deploy/package.json deploy/package.json
COPY contract/package.json contract/tsconfig.json contract/tsconfig.build.json contract/LICENSE contract/
COPY seams/LICENSE seams/LICENSE
COPY seams/policy-decision/package.json seams/policy-decision/tsconfig.json seams/policy-decision/tsconfig.build.json seams/policy-decision/
COPY packages/jcs/package.json packages/jcs/tsconfig.json packages/jcs/tsconfig.build.json packages/jcs/
COPY packages/service-kit/package.json packages/service-kit/tsconfig.json packages/service-kit/tsconfig.build.json packages/service-kit/
COPY packages/env-store/package.json packages/env-store/tsconfig.json packages/env-store/tsconfig.build.json packages/env-store/
COPY packages/registry/package.json packages/registry/tsconfig.json packages/registry/tsconfig.build.json packages/registry/
COPY packages/credentials/package.json packages/credentials/tsconfig.json packages/credentials/tsconfig.build.json packages/credentials/
COPY packages/attribution/package.json packages/attribution/tsconfig.json packages/attribution/tsconfig.build.json packages/attribution/
COPY packages/envelope/package.json packages/envelope/tsconfig.json packages/envelope/tsconfig.build.json packages/envelope/
COPY packages/authority/package.json packages/authority/tsconfig.json packages/authority/tsconfig.build.json packages/authority/
COPY packages/policy-decision/package.json packages/policy-decision/tsconfig.json packages/policy-decision/tsconfig.build.json packages/policy-decision/
COPY packages/config/package.json packages/config/tsconfig.json packages/config/tsconfig.build.json packages/config/
COPY packages/perimeter/package.json packages/perimeter/tsconfig.json packages/perimeter/tsconfig.build.json packages/perimeter/
COPY services/event-ingest/package.json services/event-ingest/tsconfig.json services/event-ingest/tsconfig.build.json services/event-ingest/
RUN pnpm install --frozen-lockfile
COPY contract/generated/ contract/generated/
COPY contract/conventions/components.openapi.yaml contract/conventions/
COPY contract/event-ingest.openapi.yaml contract/envelope.schema.json contract/delivery.schema.json contract/
COPY seams/policy-decision/src/ seams/policy-decision/src/
COPY packages/jcs/src/ packages/jcs/src/
COPY packages/service-kit/src/ packages/service-kit/src/
COPY packages/env-store/src/ packages/env-store/src/
COPY packages/registry/src/ packages/registry/src/
COPY packages/credentials/src/ packages/credentials/src/
COPY packages/attribution/src/ packages/attribution/src/
COPY packages/envelope/src/ packages/envelope/src/
COPY packages/authority/src/ packages/authority/src/
COPY packages/policy-decision/src/ packages/policy-decision/src/
COPY packages/config/src/ packages/config/src/
COPY packages/config/schema/ packages/config/schema/
COPY packages/perimeter/src/ packages/perimeter/src/
COPY services/event-ingest/src/ services/event-ingest/src/
RUN pnpm exec tsc -b services/event-ingest/tsconfig.build.json \
 && pnpm --filter @soorma/event-ingest deploy --prod --legacy /out

FROM gcr.io/distroless/nodejs26-debian13:nonroot@sha256:33c86a63859efc2ebd88ea0a355863582ec6f1220d048de62baffb2584e709b3
WORKDIR /app
COPY --from=build /out/ /app/
ENV NODE_ENV=production \
    SOORMA_CONFIG=/etc/soorma/tenancy.yaml
USER nonroot
EXPOSE 8443
CMD ["dist/main.js"]
