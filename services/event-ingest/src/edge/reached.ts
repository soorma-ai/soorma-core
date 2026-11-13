// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Whether a request reached one of S4's handlers. A refusal Fastify makes
// before any handler (step 1: a body over its route's limit) is logged by the
// edge's onResponse hook as ingest.refused, so every refusal writes exactly
// one security event (BR-RF-ET-01); a handler's own refusals are logged where
// they are made, and are not logged twice.
import type { FastifyRequest } from 'fastify';

const REACHED = Symbol('soorma.event-ingest.reached');

type Marked = FastifyRequest & { [REACHED]?: true };

export function markReached(request: FastifyRequest): void {
  (request as Marked)[REACHED] = true;
}

export function reached(request: FastifyRequest): boolean {
  return (request as Marked)[REACHED] === true;
}
