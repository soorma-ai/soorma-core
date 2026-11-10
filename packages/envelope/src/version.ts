// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Check-order step 5 on a call with a draft (U3 D-AE-12; BR-VR-01 to 05):
//
// 1. A body that is not a JSON object is malformed_request, pointer ""
// 2. A missing or non-string clientContractVersion is
//    unsupported_contract_version: declaring no version is not declaring an
//    accepted one (BR-VER-04)
// 3. A version not in the accepted set, by exact match, is
//    unsupported_contract_version (BR-VER-03)
// 4. Then the header: Soorma-Contract-Version sent more than once, or
//    different from the draft's value, is malformed_request naming the
//    header. Not sending it is allowed
//
// Step 5 reads only clientContractVersion (BR-VR-05). The accepted set is an
// input (P1's, D-AE-25), so this package does not depend on P1.
import { isObject, ok, own, refuse, type Result } from './refusal.ts';

export const CONTRACT_VERSION_HEADER = 'Soorma-Contract-Version';

export function checkVersion(
  body: unknown,
  headerValues: readonly string[],
  acceptedVersions: readonly string[],
): Result<Record<string, unknown>> {
  if (!isObject(body)) return refuse('malformed_request', 'body_not_object', [{ pointer: '' }]);
  const version = own(body, 'clientContractVersion');
  if (typeof version !== 'string') return refuse('unsupported_contract_version', 'version_missing');
  if (!acceptedVersions.includes(version))
    return refuse('unsupported_contract_version', 'version_not_accepted');
  if (headerValues.length > 1 || (headerValues.length === 1 && headerValues[0] !== version))
    return refuse('malformed_request', 'version_header_mismatch', [
      { header: CONTRACT_VERSION_HEADER },
    ]);
  return ok(body);
}
