// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S3's request validation against the contract itself (as S2, NFR-EHA-17):
// @soorma/service-kit's validator over data-gateway.openapi.yaml, compiled
// once at start-up. Only exchangeBootstrap takes a body.
import { ContractValidator as ServiceContractValidator } from '@soorma/service-kit/http';

export type RequestSchema = 'BootstrapRequest';

export class ContractValidator extends ServiceContractValidator<RequestSchema> {
  constructor() {
    super({ document: 'data-gateway.openapi.yaml', schemas: ['BootstrapRequest'] });
  }
}
