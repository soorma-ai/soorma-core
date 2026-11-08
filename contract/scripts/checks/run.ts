// SPDX-License-Identifier: Apache-2.0
//
// Runs every contract check and exits non-zero on any finding:
//   node scripts/checks/run.ts
import { compatFindings, loadFixtures, parseClassifications, readChangelog } from './compat.ts';
import { loadContract, type Finding } from './model.ts';
import { metaFindingsOnDisk } from './meta.ts';
import { contractFindings } from './rules.ts';
import { spdxFindingsOnDisk } from './spdx.ts';
import { createValidator } from '../validator.ts';

export function allContractFindings(): Finding[] {
  const contract = loadContract();
  const { validate } = createValidator(contract);
  return [
    ...contractFindings(contract),
    ...spdxFindingsOnDisk(),
    ...metaFindingsOnDisk(contract),
    ...compatFindings(loadFixtures(), validate, parseClassifications(readChangelog())),
  ];
}

if (import.meta.main) {
  const findings = allContractFindings();
  for (const f of findings) console.error(`${f.check}: ${f.location}: ${f.message}`);
  if (findings.length > 0) {
    console.error(`${findings.length} contract finding(s).`);
    process.exitCode = 1;
  } else {
    console.log('Contract checks passed.');
  }
}
