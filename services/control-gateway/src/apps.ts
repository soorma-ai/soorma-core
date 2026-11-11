// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S2's one NestJS application, the edge (NP-EHA-12): service-kit's Fastify
// adapter (TLS 1.3, 16 KiB bodies, request ids, the Soorma headers), the
// request throttle on its hooks (NP-EHA-05), and the Problem filter with one
// Retry-After for every 503 (5 seconds) and a security event for each.
import { NestFactory } from '@nestjs/core';
import type { NestFastifyApplication } from '@nestjs/platform-fastify';
import { UnavailableError } from '@soorma/service-kit';
import { createAdapter, ProblemFilter, type ListenerTls } from '@soorma/service-kit/http';
import { EdgeModule } from './edge/edge.module.ts';
import { OrgLevelUnavailableError } from './org-level.ts';
import type { Runtime } from './runtime.ts';
import { RETRY_AFTER_SECONDS } from './settings.ts';
import { installRequestThrottle } from './throttle.ts';

/** Which security event a 503 logs (NFR-EHA-19), from what failed. */
export function logUnavailable(rt: Runtime, requestId: string, error: UnavailableError): void {
  if (error instanceof OrgLevelUnavailableError)
    rt.log.event('orglevel.unavailable', requestId, { code: error.operation });
  else if (error.message === 's1_calls')
    rt.log.event('throttle.refused', requestId, { code: 's1_calls' });
  else if (error.message === 'no verify keys held')
    rt.log.event('orglevel.unavailable', requestId, { code: 'verify_keys' });
  else rt.log.event('store.unavailable', requestId);
}

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
      onUnavailable: (requestId, error) => logUnavailable(runtime, requestId, error),
    }),
  );
  await app.init();
  return app;
}
