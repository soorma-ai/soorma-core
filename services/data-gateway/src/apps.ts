// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S3's one NestJS application, the edge (as S2's, NP-EHA-12): service-kit's
// Fastify adapter (TLS 1.3, 16 KiB bodies, request ids, the Soorma headers),
// the request throttle on its hooks, and the Problem filter with one
// Retry-After for every 503 (5 seconds) and a security event for each.
import { NestFactory } from '@nestjs/core';
import type { NestFastifyApplication } from '@nestjs/platform-fastify';
import { createAdapter, ProblemFilter, type ListenerTls } from '@soorma/service-kit/http';
import { EdgeModule } from './edge/edge.module.ts';
import type { Runtime } from './runtime.ts';
import { RETRY_AFTER_SECONDS } from './settings.ts';
import { installRequestThrottle } from './throttle.ts';

export async function createEdgeApp(
  runtime: Runtime,
  tls?: ListenerTls,
): Promise<NestFastifyApplication> {
  const adapter = createAdapter(tls);
  installRequestThrottle(adapter.getInstance(), runtime.requests, (requestId) =>
    runtime.log.event('throttle.refused', requestId, { code: 'requests' }),
  );
  const app = await NestFactory.create<NestFastifyApplication>(
    EdgeModule.forRuntime(runtime),
    adapter,
    { bodyParser: false, logger: false, abortOnError: false },
  );
  app.useGlobalFilters(
    new ProblemFilter(runtime.log, {
      retryAfterSeconds: RETRY_AFTER_SECONDS,
      onUnavailable: (requestId) => runtime.log.event('store.unavailable', requestId),
    }),
  );
  await app.init();
  return app;
}
