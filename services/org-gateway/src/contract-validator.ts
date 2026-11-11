// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S1's request validation against the contract itself (NFR-OI-28):
// @soorma/service-kit's validator over org-gateway.openapi.yaml, compiled once
// at start-up (U4 NP-EHA-15).
import { ContractValidator as ServiceContractValidator } from '@soorma/service-kit/http';

export type RequestSchema =
  'FirstAuthenticateRequest' | 'AuthenticateRequest' | 'ChangeMaterialRequest';

export class ContractValidator extends ServiceContractValidator<RequestSchema> {
  constructor() {
    super({
      document: 'org-gateway.openapi.yaml',
      schemas: ['FirstAuthenticateRequest', 'AuthenticateRequest', 'ChangeMaterialRequest'],
    });
  }

  /**
   * Any definition of the S1 document or the shared components, for checking
   * responses against the contract in tests (TC-OI-023).
   */
  override conforms(
    document: 'org-gateway' | 'components' | 'service',
    name: string,
    value: unknown,
  ): boolean {
    return super.conforms(document === 'components' ? 'components' : 'service', name, value);
  }
}
