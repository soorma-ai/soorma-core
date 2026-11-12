// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The request throttle, as S2's (NP-EHA-05; NFR-EHA-04; D-CG-EHA-09; U6
// D-CG-AC-08): at most 64 requests in flight per S3 instance. A permit is taken in Fastify's
// onRequest hook, before the body is read, so a flood holds at most 64 × 16
// KiB of bodies. It is released in both onResponse and onRequestAbort,
// through a release-once guard (the user's change), so a request answered and
// aborted, in either order, frees its permit exactly once. A request aborted
// while still waiting leaves the queue and holds nothing. A wait past 1 second
// is unavailable (503, Retry-After 5) and logs throttle.refused.
import {
  AcquireAbortedError,
  ProblemError,
  UnavailableError,
  type Release,
  type Semaphore,
} from '@soorma/service-kit';
import { sendProblem } from '@soorma/service-kit/http';
import type { FastifyInstance, FastifyRequest } from 'fastify';
import { RETRY_AFTER_SECONDS } from './settings.ts';

const RELEASE = Symbol('soorma.request-permit');

type Held = FastifyRequest & { [RELEASE]?: Release };

export function installRequestThrottle(
  fastify: FastifyInstance,
  permits: Semaphore,
  onRefused: (requestId: string) => void,
): void {
  fastify.addHook('onRequest', async (request, reply) => {
    const controller = new AbortController();
    const socket = request.raw.socket as { once?: unknown; off?: unknown } | undefined;
    const onClose = (): void => controller.abort();
    const watch = typeof socket?.once === 'function';
    if (watch) request.raw.socket.once('close', onClose);
    try {
      (request as Held)[RELEASE] = await permits.acquire(controller.signal);
    } catch (error) {
      if (error instanceof AcquireAbortedError) return reply.hijack();
      if (!(error instanceof UnavailableError)) throw error;
      onRefused(request.id);
      sendProblem(
        reply,
        request.id,
        new ProblemError('unavailable', { retryAfterSeconds: RETRY_AFTER_SECONDS }),
      );
      return reply;
    } finally {
      if (watch) request.raw.socket.off('close', onClose);
    }
  });
  const release = (request: FastifyRequest): void => {
    (request as Held)[RELEASE]?.();
  };
  fastify.addHook('onResponse', (request, _reply, done) => {
    release(request);
    done();
  });
  fastify.addHook('onRequestAbort', (request, done) => {
    release(request);
    done();
  });
}
