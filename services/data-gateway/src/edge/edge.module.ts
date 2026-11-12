// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The edge listener's NestJS module: S3's two contract operations
// (contract/data-gateway.openapi.yaml). S3 has no internal listener: nothing
// calls S3 but agent instances.
import { Controller, Inject, Module, Post, Req, Res, type DynamicModule } from '@nestjs/common';
import type { FastifyReply, FastifyRequest } from 'fastify';
import type { Runtime } from '../runtime.ts';
import { EdgeHandlers } from './edge-handlers.ts';

export const EDGE_HANDLERS = Symbol('soorma.data-gateway.edge.handlers');

@Controller()
export class EdgeController {
  private readonly handlers: EdgeHandlers;

  constructor(@Inject(EDGE_HANDLERS) handlers: EdgeHandlers) {
    this.handlers = handlers;
  }

  @Post('agent-credentials')
  exchangeBootstrap(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    return this.handlers.exchangeBootstrap(request, reply);
  }

  @Post('agent-credentials/current/renewal')
  renewAgentCredential(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    return this.handlers.renewAgentCredential(request, reply);
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
