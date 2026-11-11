// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Check-order step 6: the draft (U3 BR-DV-01 to 05; D-AE-17, 18).
//
// The draft is validated against U1's Draft schema (envelope.schema.json),
// which includes inbound.envelope against the open Envelope schema, then
// against the trace-context rules checked in code. One code wins, in a fixed
// precedence (D-AE-18):
//
// 1. stamped_field_set: a platform-stamped field at the draft's top level,
//    whatever else fails (BR-DR-10; BR-DV-04: origin mode and a re-broadening
//    record included, at every hop)
// 2. unknown_field: a field the draft's top level, or its traceContext, does
//    not define
// 3. malformed_request: any other failure, a trace-context rule included
//
// The winning code is picked from all the errors. errors[] then lists the
// fields failing with that code, ordered by pointer, at most MAX_ERRORS of
// them: the first 10 by pointer, as S1 caps its own (BR-DV-03; D-AE-18). A
// draft that fails is refused; nothing in it is ever overwritten (BR-DV-05).
//
// Ajv's 2020 build, strict, with V8's default RegExp (NFR-AE-01; T-AE-01),
// created and compiled once, when the validator is created (NFR-AE-03).
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { Ajv2020, type ErrorObject, type ValidateFunction } from 'ajv/dist/2020.js';
import { byPointer, isObject, ok, own, refuse, type FieldError, type Result } from './refusal.ts';
import { traceparentProblems, tracestateProblems } from './trace-context.ts';

const require = createRequire(import.meta.url);
const SCHEMA_ID = 'https://soorma.ai/contract/envelope.schema.json';

/** At most this many entries in errors[], the first by pointer: S1's MAX_ERRORS (D-AE-18). */
export const MAX_ERRORS = 10;

/** The draft's platform-stamped fields, forbidden by name (BR-DR-02). */
export const STAMPED_FIELDS: readonly string[] = Object.freeze([
  'envelopeVersion',
  'scope',
  'originMode',
  'delegatingPrincipal',
  'actorChain',
  'reBroadening',
]);

/** A draft after steps 5 and 6. `inbound.envelope` is open and as received. */
export interface ValidDraft {
  readonly clientContractVersion: string;
  readonly traceContext: { readonly traceparent: string; readonly tracestate?: string };
  readonly inbound?: { readonly envelope: Record<string, unknown>; readonly seal: string };
}

export interface DraftValidator {
  validate(draft: Record<string, unknown>): Result<ValidDraft>;
}

function escapePointer(segment: string): string {
  return segment.replace(/~/g, '~0').replace(/\//g, '~1');
}

function pointerOf(e: ErrorObject): string {
  const params = e.params as { additionalProperty?: string; missingProperty?: string };
  if (params.additionalProperty !== undefined)
    return `${e.instancePath}/${escapePointer(params.additionalProperty)}`;
  if (params.missingProperty !== undefined)
    return `${e.instancePath}/${escapePointer(params.missingProperty)}`;
  return e.instancePath;
}

/** One entry per pointer, ordered by pointer, the first MAX_ERRORS kept. */
function unique(errors: FieldError[]): FieldError[] {
  const seen = new Map<string, FieldError>();
  for (const e of errors) if (!seen.has(e.pointer ?? '')) seen.set(e.pointer ?? '', e);
  return byPointer([...seen.values()]).slice(0, MAX_ERRORS);
}

/** Builds the validator: Ajv created, and the Draft schema compiled, once. */
export function createDraftValidator(): DraftValidator {
  const schema = JSON.parse(
    readFileSync(require.resolve('@soorma/contract/envelope.schema.json'), 'utf8'),
  ) as object;
  const ajv = new Ajv2020({ strict: true, allErrors: true });
  ajv.addSchema(schema);
  const compiled: ValidateFunction | undefined = ajv.getSchema(`${SCHEMA_ID}#/$defs/Draft`);
  if (!compiled) throw new Error('the contract defines no Draft schema');
  const validateSchema: ValidateFunction = compiled;

  return Object.freeze({
    validate(draft: Record<string, unknown>): Result<ValidDraft> {
      // 1. Stamped fields, whatever else fails.
      const stamped = STAMPED_FIELDS.filter((f) => Object.hasOwn(draft, f));
      if (stamped.length > 0)
        return refuse(
          'stamped_field_set',
          'stamped_field',
          byPointer(stamped.map((f) => ({ pointer: `/${f}` }))),
        );

      const schemaErrors = validateSchema(draft) ? [] : (validateSchema.errors ?? []);

      // 2. Unknown fields at the top level or in the draft's traceContext.
      const unknown = schemaErrors.filter(
        (e) =>
          e.keyword === 'additionalProperties' &&
          (e.instancePath === '' || e.instancePath === '/traceContext'),
      );
      if (unknown.length > 0)
        return refuse(
          'unknown_field',
          'unknown_field',
          unique(unknown.map((e) => ({ pointer: pointerOf(e) }))),
        );

      // 3. Every other failure: the schema's, then the rules checked in code
      //    on any trace-context value whose form the schema accepted.
      const errors: FieldError[] = schemaErrors.map((e) => ({
        pointer: pointerOf(e),
        detail: e.message ?? 'invalid',
      }));
      const failed = (pointer: string): boolean => errors.some((e) => e.pointer === pointer);
      const traceContext = own(draft, 'traceContext');
      const traceparent = isObject(traceContext) ? own(traceContext, 'traceparent') : undefined;
      const tracestate = isObject(traceContext) ? own(traceContext, 'tracestate') : undefined;
      const traceErrors = [
        ...(typeof traceparent === 'string' && !failed('/traceContext/traceparent')
          ? traceparentProblems(traceparent)
          : []),
        ...(typeof tracestate === 'string' && !failed('/traceContext/tracestate')
          ? tracestateProblems(tracestate)
          : []),
      ];
      if (errors.length > 0 || traceErrors.length > 0)
        return refuse(
          'malformed_request',
          errors.length > 0 ? 'schema' : 'trace_context',
          unique([...errors, ...traceErrors]),
        );

      return ok(draft as unknown as ValidDraft);
    },
  });
}
