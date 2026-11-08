// SPDX-License-Identifier: Apache-2.0
// The written conventions carry each statement the contract makes:
// TC-WC-004, 005, 018 (step 4), 019 (step 4), 020 (step 6), 025, 026, 028, 029.
import { describe, expect, it } from 'vitest';
import { convention } from './helpers.ts';

const readme = convention('README.md');
const envelope = convention('envelope.md');
const errors = convention('errors.md');
const credentials = convention('credentials.md');
const identifiers = convention('identifiers.md');
const versioning = convention('versioning.md');
const preRelease = convention('pre-release.md');

describe('TC-WC-004: the contract declares its pre-release status', () => {
  it('states the version, the status, and what pre-release covers', () => {
    expect(readme).toContain('Contract version: `0.1.0` · Status: pre-release');
    expect(preRelease).toContain(
      'The operations, error codes, and credential presentation may change between `0.y` versions',
    );
    expect(preRelease).toContain('Envelope v1 does not');
  });

  it('states that event delivery semantics are unspecified', () => {
    expect(preRelease).toContain('Event delivery semantics are unspecified at this version');
    expect(preRelease).toContain('live subscribers only');
    expect(preRelease).toContain('no durability, ordering, redelivery, or acknowledgement');
  });
});

describe('TC-WC-005: bootstrap and renewal carry no envelope', () => {
  it('lists the envelope-bearing operations', () => {
    expect(envelope).toMatch(/\| Publish \| S4 \| A draft in the request \|/);
    expect(envelope).toMatch(
      /\| Subscribe \| S4 \| A draft in the request; a Delivery per event on the stream \|/,
    );
    expect(envelope).toMatch(/\| Bootstrap exchange \| S3 \| None \|/);
    expect(envelope).toMatch(/\| Credential renewal \| S3 \| None \|/);
    expect(envelope).toMatch(/\| Every direct human operation \| S1, S2 \| None \|/);
    expect(preRelease).toContain('The bootstrap exchange and credential renewal carry no envelope');
  });

  it('states the rules for unlisted and new operations', () => {
    expect(envelope).toContain(
      'An operation not listed as envelope-bearing does not accept a draft',
    );
    expect(envelope).toContain(
      'A surface that adds an envelope-bearing operation adds a row here. That is a contract change',
    );
  });
});

describe('TC-WC-018, 019, 020: maxChainDepth and the rules checked in code', () => {
  it('states maxChainDepth', () => {
    expect(envelope).toContain('maxChainDepth` is 32 for envelope v1');
  });

  it.each([
    'Each `hop` in `reBroadening` is an index into `actorChain`',
    'No `hop` appears twice in `reBroadening`',
    'A `traceparent` version of `ff` is invalid',
    'An all-zero trace id is invalid',
    'An all-zero parent id is invalid',
    '`tracestate` has at most 32 list members',
  ])('lists "%s" as checked in code', (rule) => {
    expect(envelope).toContain(rule);
  });

  it('states that trace context is validated for form only, with no spans', () => {
    expect(envelope).toContain(
      'Trace context is validated for form only. The platform never interprets the values, and emits no spans',
    );
  });
});

describe('TC-WC-025: error codes, disclosure, and the check order', () => {
  it.each([
    ['malformed_request', 400],
    ['unknown_field', 400],
    ['stamped_field_set', 400],
    ['invalid_inbound_context', 400],
    ['chain_too_deep', 400],
    ['envelope_too_large', 400],
    ['unsupported_contract_version', 400],
    ['credential_refused', 401],
    ['credential_expired', 401],
    ['forbidden', 403],
    ['payload_too_large', 413],
    ['too_many_attempts', 429],
    ['unavailable', 503],
    ['internal_error', 500],
  ])('lists %s with status %i', (code, status) => {
    expect(errors).toMatch(new RegExp(`\\| \`${code}\` \\| ${status} \\|`));
  });

  it('gives no detail for trust failures, and states the code set is open', () => {
    expect(errors).toMatch(
      /\| `invalid_inbound_context` \| 400 \| [^|]+ \| None: one code for every cause \|/,
    );
    expect(errors).toMatch(/\| `credential_refused` \| 401 \| [^|]+ \| None \|/);
    expect(errors).toMatch(/\| `forbidden` \| 403 \| [^|]+ \| None \|/);
    expect(errors).toContain('The code set is open');
    expect(errors).toContain('Only the validation codes carry a pointer');
  });

  it('states the disclosure rules', () => {
    expect(errors).toContain(
      "credential_expired` is returned only after the credential verifies with this environment's material",
    );
    expect(errors).toContain('too_many_attempts` does not reveal whether its subject exists');
    expect(errors).toContain('No response carries a stack trace');
  });

  it('states the ten-step check order, stamped fields first and the envelope size last', () => {
    const order = errors.slice(errors.indexOf('## Check order'));
    for (let step = 1; step <= 10; step++) expect(order).toContain(`${step}. `);
    expect(order).toContain('stamped fields before unknown fields');
    expect(order).toContain('The size of the envelope to be stamped, last');
  });

  it('states the response headers', () => {
    expect(errors).toContain('A 401 carries `WWW-Authenticate: Bearer`');
    expect(errors).toContain('A 429 and a 503 carry `Retry-After`');
  });

  it('states what soorma-core emits and that a client accepts any problem (BR-ERR-08)', () => {
    expect(errors).toContain(
      'Every Problem soorma-core emits carries `type`, `title`, `status`, `code`, and `instance`',
    );
    expect(errors).toContain('`type` is `urn:soorma:problem:{code}`');
    expect(errors).toContain(
      "`instance` is `urn:soorma:request:{request id}`, equal to the response's `Soorma-Request-Id`",
    );
    expect(errors).toContain('A client accepts any problem');
  });
});

describe('TC-WC-026: credential presentation', () => {
  it('states the presentation rules, prefixes, syntax, and material', () => {
    expect(credentials).toContain(
      'A credential is presented only as `Authorization: Bearer {credential}`. One per request',
    );
    for (const prefix of ['soorma_ac_', 'soorma_ec_', 'soorma_si_', 'soorma_dc_'])
      expect(credentials).toContain(`\`${prefix}\``);
    expect(credentials).toContain(
      'The prefix selects how a credential is checked. It never admits one',
    );
    expect(credentials).toContain('its verified kind must match its prefix');
    expect(credentials).toContain('is an RFC 6750 `b64token`');
    expect(credentials).toContain('at most 4096 characters');
    expect(credentials).toContain('They go in a request body, never in `Authorization`');
    expect(credentials).toContain('Each is at most 256 characters');
    expect(credentials).toContain('The `Soorma-Delegation` header is reserved');
    expect(credentials).toContain('No cookies');
    expect(credentials).toContain('No CORS');
  });
});

describe('TC-WC-022 and 028: identifiers and versioning', () => {
  it('states exact comparison, ASCII-only human identifiers, and compatible widening', () => {
    expect(identifiers).toContain('case-sensitive and compared exactly');
    expect(identifiers).toContain(
      'Human principal identifiers are ASCII-only in this contract version',
    );
    expect(identifiers).toContain('widening a pattern or a length later is compatible');
  });

  it('states the version form, the accepted set, the refusal, and the classification', () => {
    expect(versioning).toContain('SemVer `0.y.z`');
    expect(versioning).toContain(
      'The first published version is `0.1.0`, at the git tag `contract-v0.1.0`',
    );
    expect(versioning).toContain('The accepted set in this version is `{0.1.0}`');
    expect(versioning).toContain('exact; no ranges');
    expect(versioning).toContain(
      'A version once accepted stays accepted until a published deprecation window, longer than zero, elapses',
    );
    expect(versioning).toContain('`unsupported_contract_version`, listing `supportedVersions`');
    expect(versioning).toContain('Not in this contract version: no breaking change to envelope v1');
    expect(versioning).toMatch(/Widen an identifier pattern or length \| Compatible/);
  });
});

describe('TC-WC-029: the remaining pre-release and trust statements', () => {
  it.each([
    [preRelease, 'The accepted permission identifiers may widen in a compatible version'],
    [preRelease, 'only the plane-declared identifiers are accepted'],
    [
      preRelease,
      'A draft never carries origin mode. Accepting an asserted origin later would be additive',
    ],
    [preRelease, 'Delegation-credential presentation will be added without a breaking change'],
    [preRelease, 'The `Soorma-Delegation` header and the `soorma_dc_` prefix are reserved'],
    [preRelease, '`maxChainDepth` is 32 for envelope v1'],
    [preRelease, 'The envelope bound is 16 KiB, measured on the RFC 8785 (JCS) serialization'],
    [preRelease, 'Received identifiers are opaque strings; do not validate their syntax'],
    [envelope, 'The envelope carries assertions, not proof. It is never self-authenticating'],
    [
      envelope,
      'The seal is opaque. A client forwards it unchanged and must not treat it as proof it can check',
    ],
    [
      envelope,
      'The Delivery payload bound is set by the event transport unit (U7) and published there',
    ],
  ])('states: %#', (text, statement) => {
    expect(text).toContain(statement);
  });
});
