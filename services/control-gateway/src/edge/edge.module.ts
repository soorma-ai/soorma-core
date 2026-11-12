// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The edge listener's NestJS module: the four contract operations of U4, and
// U5's registerAgent and issueRegistrationSecret. S2 has no
// internal listener: nothing calls S2 but clients (NP-EHA-12).
import { Controller, Inject, Module, Post, Req, Res, type DynamicModule } from '@nestjs/common';
import type { FastifyReply, FastifyRequest } from 'fastify';
import type { Runtime } from '../runtime.ts';
import { EdgeHandlers } from './edge-handlers.ts';

export const EDGE_HANDLERS = Symbol('soorma.control-gateway.edge.handlers');

@Controller()
export class EdgeController {
  private readonly handlers: EdgeHandlers;

  constructor(@Inject(EDGE_HANDLERS) handlers: EdgeHandlers) {
    this.handlers = handlers;
  }

  @Post('environment-credentials')
  issue(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    return this.handlers.issue(request, reply);
  }

  @Post('environment-credentials/current/renewal')
  renew(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    return this.handlers.renew(request, reply);
  }

  @Post('environment-credentials/current/end')
  end(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    return this.handlers.end(request, reply);
  }

  @Post('grants')
  grant(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    return this.handlers.grant(request, reply);
  }

  @Post('registrations')
  registerAgent(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    return this.handlers.registerAgent(request, reply);
  }

  @Post('registration-secrets')
  issueRegistrationSecret(
    @Req() request: FastifyRequest,
    @Res() reply: FastifyReply,
  ): Promise<void> {
    return this.handlers.issueRegistrationSecret(request, reply);
  }
}

@Module({})
export class EdgeModule {
  static forRuntime(runtime: Runtime): DynamicModule {
    return {
      module: EdgeModule,
      controllers: [EdgeController],
      providers: [{ provide: EDGE_HANDLERS, useValue: new EdgeHandlers(runtime) }],
    };
  }
}
