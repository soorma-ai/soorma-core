// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The internal listener (BR-INT; P-06, P-07; logical-components §5): a
// separate NestJS application on its own Fastify instance and port, with the
// three read-only operations U4 calls. Every call must carry a signed request
// from a configured environment, bound to its method, full target, and body.
// No endpoint here is unauthenticated, and network location is never the
// check (I3). Any failure is a refusal with no detail, logged as
// internal.call_refused.
import {
  Controller,
  Get,
  Inject,
  Module,
  Param,
  Req,
  Res,
  type DynamicModule,
} from '@nestjs/common';
import { verifyInternalRequest } from '@soorma/org-identity';
import { ProblemError, rawHeaderValues } from '@soorma/perimeter';
import type { FastifyReply, FastifyRequest } from 'fastify';
import { rawBody } from '../http.ts';
import type { Runtime } from '../runtime.ts';

export const INTERNAL_RUNTIME = Symbol('soorma.internal.runtime');

const IDENTIFIER = /^[A-Za-z0-9!#$%&'*+/=?^_`{|}~.@:-]{1,256}$/;

export class InternalHandlers {
  private readonly rt: Runtime;

  constructor(runtime: Runtime) {
    this.rt = runtime;
  }

  /** The calling environment, or a refusal (logged, no detail). */
  async caller(request: FastifyRequest): Promise<string> {
    // Every internal operation takes no body. Fastify does not read a body on
    // GET, so one sent anyway could not be hashed as received (P-06 bsh):
    // a request declaring a body is refused.
    const length = Number(request.headers['content-length'] ?? 0);
    const declaresBody = length > 0 || request.headers['transfer-encoding'] !== undefined;
    const environment = declaresBody
      ? undefined
      : await verifyInternalRequest(
          {
            method: request.method,
            target: request.raw.url ?? '',
            body: rawBody(request),
            authorization: rawHeaderValues(request.raw.rawHeaders, 'Authorization'),
          },
          this.rt.keys,
          this.rt.organization,
          this.rt.clock.now(),
        );
    if (environment === undefined) {
      this.rt.log.event('internal.call_refused', request.id);
      throw new ProblemError('credential_refused');
    }
    return environment;
  }

  json(reply: FastifyReply, body: unknown): void {
    void reply
      .status(200)
      .header('Content-Type', 'application/json; charset=utf-8')
      .send(JSON.stringify(body));
  }
}

@Controller()
export class InternalController {
  private readonly handlers: InternalHandlers;
  private readonly rt: Runtime;

  constructor(@Inject(INTERNAL_RUNTIME) runtime: Runtime) {
    this.rt = runtime;
    this.handlers = new InternalHandlers(runtime);
  }

  /** verifyOnlyMaterial: the verify keys as a JWKS, public only (BR-INT-03). */
  @Get('verify-keys')
  async verifyKeys(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    await this.handlers.caller(request);
    this.handlers.json(reply, this.rt.identity.verifyOnlyMaterial());
  }

  /** principalExists: yes or no, and nothing else (BR-INT-04). */
  @Get('principals/exists')
  async principalExists(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    await this.handlers.caller(request);
    const query = request.query as Record<string, unknown>;
    const { organization, principal } = query;
    if (
      Object.keys(query).length !== 2 ||
      typeof organization !== 'string' ||
      typeof principal !== 'string' ||
      !IDENTIFIER.test(principal) ||
      organization.length === 0 ||
      organization.length > 64
    )
      throw new ProblemError('malformed_request', {
        errors: [{ pointer: '', detail: 'organization and principal are each required once' }],
      });
    const exists =
      organization === this.rt.organization &&
      (await this.rt.identity.principalExists({ organization, principal }));
    this.handlers.json(reply, { exists });
  }

  /** signInStatus: live, ended, or unknown, and nothing else (BR-INT-05). */
  @Get('sign-ins/:id/status')
  async signInStatus(
    @Param('id') id: string,
    @Req() request: FastifyRequest,
    @Res() reply: FastifyReply,
  ): Promise<void> {
    await this.handlers.caller(request);
    const status = /^[0-9a-f]{32}$/.test(id) ? await this.rt.identity.signInStatus(id) : 'unknown';
    this.handlers.json(reply, { status });
  }
}

@Module({})
export class InternalModule {
  static forRuntime(runtime: Runtime): DynamicModule {
    return {
      module: InternalModule,
      controllers: [InternalController],
      providers: [{ provide: INTERNAL_RUNTIME, useValue: runtime }],
    };
  }
}
