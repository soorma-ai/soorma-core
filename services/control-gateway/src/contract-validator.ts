// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S2's request validation against the contract itself (NFR-EHA-17):
// @soorma/service-kit's validator over control-gateway.openapi.yaml, compiled
// once at start-up. Only grantToHuman takes a body.
import { ContractValidator as ServiceContractValidator } from '@soorma/service-kit/http';

export type RequestSchema = 'GrantRequest' | 'RegistrationRequest' | 'RegistrationSecretRequest';

export class ContractValidator extends ServiceContractValidator<RequestSchema> {
  constructor() {
    super({
      document: 'control-gateway.openapi.yaml',
      schemas: ['GrantRequest', 'RegistrationRequest', 'RegistrationSecretRequest'],
    });
  }
}
