// SPDX-License-Identifier: Apache-2.0
//
// Which definitions are request-side and which are received-side. Kept in one
// file, for review (NFR-WC-07; BR-ID-11).
//
// Request side: what the platform accepts. Strict: every string has a maxLength,
// every array a maxItems, identifiers carry their kind's pattern.
// Received side: what a client receives. Tolerant: identifiers are plain strings
// with no pattern or maximum length, and enumerations are open.
//
// Every definition in the contract must be listed in exactly one of the two, so a
// new definition cannot skip the checks unclassified.

export const requestSide: readonly string[] = [
  'envelope.schema.json#/$defs/Draft',
  'envelope.schema.json#/$defs/DraftTraceContext',
  'envelope.schema.json#/$defs/Inbound',
  'envelope.schema.json#/$defs/ContractVersion',
  'conventions/components.openapi.yaml#/components/schemas/ConfiguredIdentifier',
  'conventions/components.openapi.yaml#/components/schemas/LogicalAgentIdentifier',
  'conventions/components.openapi.yaml#/components/schemas/PlatformReference',
  'conventions/components.openapi.yaml#/components/schemas/InstanceIdentifier',
  'conventions/components.openapi.yaml#/components/schemas/HumanPrincipalIdentifier',
  'conventions/components.openapi.yaml#/components/schemas/PermissionIdentifier',
];

export const receivedSide: readonly string[] = [
  'envelope.schema.json#/$defs/Envelope',
  'envelope.schema.json#/$defs/Scope',
  'envelope.schema.json#/$defs/ActorReference',
  'envelope.schema.json#/$defs/ReBroadeningRecord',
  'envelope.schema.json#/$defs/DelegatingPrincipalReference',
  'envelope.schema.json#/$defs/OriginMode',
  'envelope.schema.json#/$defs/ReceivedIdentifier',
  'envelope.schema.json#/$defs/EnvelopeTraceContext',
  'delivery.schema.json#/$defs/Delivery',
  'conventions/components.openapi.yaml#/components/schemas/Problem',
  'conventions/components.openapi.yaml#/components/schemas/ProblemCode',
  'conventions/components.openapi.yaml#/components/schemas/ProblemFieldError',
];

/**
 * Definitions that are pure `$ref`s to another document's definition: classified
 * where they are defined, not here.
 */
export const aliases: readonly string[] = [
  'conventions/components.openapi.yaml#/components/schemas/Envelope',
  'conventions/components.openapi.yaml#/components/schemas/Draft',
  'conventions/components.openapi.yaml#/components/schemas/Inbound',
  'conventions/components.openapi.yaml#/components/schemas/Delivery',
  'conventions/components.openapi.yaml#/components/schemas/ContractVersion',
];

/**
 * A request-side definition may reference a received-side one only here: the
 * forwarded envelope is carried as received, open, and bounded in code by the
 * 16 KiB envelope bound (BR-DR-08, 09).
 */
export const requestToReceivedRefs: readonly string[] = [
  'envelope.schema.json#/$defs/Inbound/properties/envelope',
];
