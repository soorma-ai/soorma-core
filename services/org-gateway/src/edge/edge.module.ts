// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The edge listener's NestJS module: the five contract operations, and
// nothing of the internal interface (P-07).
import { Controller, Inject, Module, Post, Req, Res, type DynamicModule } from '@nestjs/common';
import type { FastifyReply, FastifyRequest } from 'fastify';
import type { Runtime } from '../runtime.ts';
import { EdgeHandlers } from './edge-handlers.ts';

export const EDGE_HANDLERS = Symbol('soorma.edge.handlers');

@Controller()
export class EdgeController {
  private readonly handlers: EdgeHandlers;

  constructor(@Inject(EDGE_HANDLERS) handlers: EdgeHandlers) {
    this.handlers = handlers;
  }

  @Post('first-authentication')
  firstAuthenticate(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    return this.handlers.firstAuthenticate(request, reply);
  }

  @Post('sign-ins')
  authenticate(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    return this.handlers.authenticate(request, reply);
  }

  @Post('sign-ins/current/renewal')
  renewSignIn(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    return this.handlers.renewSignIn(request, reply);
  }

  @Post('sign-ins/current/end')
  endSignIn(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    return this.handlers.endSignIn(request, reply);
  }

  @Post('material-changes')
  changeMaterial(@Req() request: FastifyRequest, @Res() reply: FastifyReply): Promise<void> {
    return this.handlers.changeMaterial(request, reply);
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
