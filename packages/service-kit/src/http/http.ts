// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The Fastify instance under each NestJS listener (U2 P-07, P-08), shared by
// every service (U4 NP-EHA-12, 15):
// - TLS 1.3 only, from the configured key and certificate (one PEM file)
// - request bodies at most 16 KiB (NFR-OI-27); larger is payload_too_large.
//   U7 (NP-ET-04): an optional map gives named routes their own limit, applied
//   as each route registers; every other path keeps 16 KiB
// - every body kept as raw bytes: S1 parses JSON itself, after the earlier
//   checks of the check order, and the internal listener hashes the exact
//   bytes (P-06)
// - a request id generated for every request, never taken from the client,
//   returned as Soorma-Request-Id on every response, with the server's
//   Soorma-Contract-Version
import { randomUUID } from 'node:crypto';
import {
  Catch,
  HttpException,
  NotFoundException,
  type ArgumentsHost,
  type ExceptionFilter,
} from '@nestjs/common';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { UnavailableError } from '../errors.ts';
import { CONTRACT_VERSION, ProblemError, problemResponse, type Refusal } from './problems.ts';
import type { FastifyReply, FastifyRequest } from 'fastify';
import type { ErrorLog } from './security-log.ts';

export const BODY_LIMIT = 16 * 1024;

export interface ListenerTls {
  /** One PEM file holding the private key and the certificate chain. */
  pem: Buffer;
}

/** U7 (NP-ET-04): per-route body limits, in bytes, by exact route path. */
export interface AdapterOptions {
  readonly routeBodyLimits?: Readonly<Record<string, number>>;
}

export function createAdapter(tls?: ListenerTls, options: AdapterOptions = {}): FastifyAdapter {
  const adapter = new FastifyAdapter({
    bodyLimit: BODY_LIMIT,
    genReqId: () => randomUUID(),
    requestIdHeader: false,
    logger: false,
    ...(tls ? { https: { key: tls.pem, cert: tls.pem, minVersion: 'TLSv1.3' as const } } : {}),
  });
  const fastify = adapter.getInstance();
  const limits = options.routeBodyLimits ?? {};
  fastify.addHook('onRoute', (route) => {
    const limit = Object.hasOwn(limits, route.url) ? limits[route.url] : undefined;
    if (limit !== undefined) route.bodyLimit = limit;
  });
  fastify.removeAllContentTypeParsers();
  fastify.addContentTypeParser('*', { parseAs: 'buffer' }, (_request, body, done) => {
    done(null, body);
  });
  fastify.addHook('onSend', (request, reply, payload, done) => {
    void reply.header('Soorma-Contract-Version', CONTRACT_VERSION);
    void reply.header('Soorma-Request-Id', request.id);
    done(null, payload);
  });
  return adapter;
}

/**
 * The Fastify adapter over P1's emission (U3 D-AE-06; BR-PE-02): the table,
 * the body, and the headers are P1's. P1's headers include the two Soorma
 * headers, with the values the onSend hook also sets.
 */
export function sendProblem(reply: FastifyReply, requestId: string, refusal: Refusal): void {
  const { status, headers, body } = problemResponse(refusal, requestId);
  void reply.status(status).headers(headers).send(JSON.stringify(body));
}

/** The raw body as received: empty when there was none. */
export function rawBody(request: FastifyRequest): Buffer {
  return Buffer.isBuffer(request.body) ? request.body : Buffer.alloc(0);
}

/**
 * One filter per listener (P-08): every refusal is a Problem; an unknown path
 * is a bare 404 (the contract defines no Problem for it); anything unexpected
 * is internal_error with no detail, logged with the request id.
 */
/** A service's choices for `unavailable` (U4 NFR-EHA-04 to 07): S1 passes none. */
export interface ProblemFilterOptions {
  /** One Retry-After for every 503, overriding the error's own (S2: 5). */
  retryAfterSeconds?: number;
  /** Called once per 503 from an UnavailableError, to log its security event. */
  onUnavailable?: (requestId: string, error: UnavailableError) => void;
}

@Catch()
export class ProblemFilter implements ExceptionFilter {
  private readonly log: ErrorLog;
  private readonly options: ProblemFilterOptions;

  constructor(log: ErrorLog, options: ProblemFilterOptions = {}) {
    this.log = log;
    this.options = options;
  }

  catch(exception: unknown, host: ArgumentsHost): void {
    const http = host.switchToHttp();
    const reply = http.getResponse<FastifyReply>();
    const request = http.getRequest<FastifyRequest>();
    if (exception instanceof ProblemError) return sendProblem(reply, request.id, exception);
    if (exception instanceof UnavailableError) {
      this.options.onUnavailable?.(request.id, exception);
      return sendProblem(
        reply,
        request.id,
        new ProblemError('unavailable', {
          retryAfterSeconds: this.options.retryAfterSeconds ?? exception.retryAfterSeconds,
        }),
      );
    }
    if (exception instanceof NotFoundException) {
      void reply.status(404).send();
      return;
    }
    // Fastify's own refusals reach the filter wrapped by NestJS as HttpException:
    // a body over the limit (413), or a request it cannot parse (400).
    if (exception instanceof HttpException && exception.getStatus() === 413)
      return sendProblem(reply, request.id, new ProblemError('payload_too_large'));
    if (exception instanceof HttpException && exception.getStatus() === 400)
      return sendProblem(reply, request.id, new ProblemError('malformed_request'));
    this.log.error(request.id, 'internal_error');
    sendProblem(reply, request.id, new ProblemError('internal_error'));
  }
}
