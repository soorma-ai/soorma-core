// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The two NestJS applications S1 runs in one process (P-07): the edge and the
// internal listener, each with its own Fastify instance, port, module graph,
// and exception filter. No route of one is registered in the other.
import { NestFactory } from '@nestjs/core';
import type { NestFastifyApplication } from '@nestjs/platform-fastify';
import { EdgeModule } from './edge/edge.module.ts';
import { createAdapter, ProblemFilter, type ListenerTls } from '@soorma/service-kit/http';
import { InternalModule } from './internal/internal.module.ts';
import type { Runtime } from './runtime.ts';

async function create(
  module: ReturnType<typeof EdgeModule.forRuntime>,
  runtime: Runtime,
  tls?: ListenerTls,
): Promise<NestFastifyApplication> {
  const app = await NestFactory.create<NestFastifyApplication>(module, createAdapter(tls), {
    bodyParser: false,
    logger: false,
    abortOnError: false,
  });
  app.useGlobalFilters(new ProblemFilter(runtime.log));
  await app.init();
  return app;
}

export function createEdgeApp(
  runtime: Runtime,
  tls?: ListenerTls,
): Promise<NestFastifyApplication> {
  return create(EdgeModule.forRuntime(runtime), runtime, tls);
}

export function createInternalApp(
  runtime: Runtime,
  tls?: ListenerTls,
): Promise<NestFastifyApplication> {
  return create(InternalModule.forRuntime(runtime), runtime, tls);
}
