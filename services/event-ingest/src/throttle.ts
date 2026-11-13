// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The request throttle, S3's module (NP-ET-13; NFR-ET-12): at most 64
// requests in flight per S4 instance. A permit is taken in Fastify's
// onRequest hook, before the body is read, so a flood holds at most 64
// bodies. It is released through a release-once guard: in onResponse, in
// onRequestAbort, and, for a subscribe, **when its stream opens**
// (releasePermit), so an open stream holds no permit and a later hook frees
// nothing twice. A request aborted while still waiting leaves the queue and
// holds nothing. A wait past 1 second is unavailable (503, Retry-After 5) and
// logs throttle.refused with code `requests`.
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

/** Frees the request's permit, once: later calls, and the hooks, free nothing. */
export function releasePermit(request: FastifyRequest): void {
  const held = request as Held;
  const release = held[RELEASE];
  held[RELEASE] = undefined;
  release?.();
}

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
  fastify.addHook('onResponse', (request, _reply, done) => {
    releasePermit(request);
    done();
  });
  fastify.addHook('onRequestAbort', (request, done) => {
    releasePermit(request);
    done();
  });
}
