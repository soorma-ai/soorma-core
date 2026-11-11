// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/service-kit/http: the NestJS and Fastify plumbing every service's
// listeners share (U4 D-CG-EHA-03). The root entry stays framework-free, so a
// module such as P1 loads no NestJS at run time.
export { ContractValidator, type ContractValidatorOptions } from './contract-validator.ts';
export {
  BODY_LIMIT,
  createAdapter,
  ProblemFilter,
  type ProblemFilterOptions,
  rawBody,
  sendProblem,
  type ListenerTls,
} from './http.ts';
export { SecurityLog, type ErrorLog, type EventFields, type LogSink } from './security-log.ts';
