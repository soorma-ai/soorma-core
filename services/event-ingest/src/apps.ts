// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S4's one NestJS application, the edge (as S3's): service-kit's Fastify
// adapter (TLS 1.3, request ids, the Soorma headers) with S4's route limits
// (NP-ET-04: publish 256 KiB, subscribe 64 KiB, every other path 16 KiB), the
// request throttle on its hooks, and the Problem filter with one Retry-After
// for every UnavailableError (5 seconds) and a security event for each; a
// refusal at step 1, made before any handler, logs ingest.refused.
import { NestFactory } from '@nestjs/core';
import type { NestFastifyApplication } from '@nestjs/platform-fastify';
import { createAdapter, ProblemFilter, type ListenerTls } from '@soorma/service-kit/http';
import { EdgeModule } from './edge/edge.module.ts';
import { reached } from './edge/reached.ts';
import type { Runtime } from './runtime.ts';
import { RETRY_AFTER_SECONDS, ROUTE_BODY_LIMITS } from './settings.ts';
import { installRequestThrottle } from './throttle.ts';

export async function createEdgeApp(
  runtime: Runtime,
  tls?: ListenerTls,
): Promise<NestFastifyApplication> {
  const adapter = createAdapter(tls, { routeBodyLimits: ROUTE_BODY_LIMITS });
  const fastify = adapter.getInstance();
  installRequestThrottle(fastify, runtime.requests, (requestId) =>
    runtime.log.event('throttle.refused', requestId, { code: 'requests' }),
  );
  // Step 1's refusal is Fastify's, before any handler: its one security event.
  fastify.addHook('onResponse', (request, reply, done) => {
    if (reply.statusCode === 413 && !reached(request))
      runtime.log.agentEvent('ingest.refused', request.id, {
        code: 'payload_too_large',
        reason: 'body_limit',
      });
    done();
  });
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
