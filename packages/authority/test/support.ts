// SPDX-License-Identifier: FSL-1.1-ALv2
// Fixtures for P3's tests: the narrative's Common Fixtures (construction
// pass). admission(E), facts, humans, context(X), ring(E), ring(E2),
// sealed(env, X), and the collecting security log. Every key is fixed test
// material, never a production secret.
import { createSealer, loadSealKeyRing, type Sealer } from '@soorma/envelope';
import { canonicalize } from '@soorma/jcs';
import { createPolicyDecision, inMemoryGrantSource } from '@soorma/policy-decision';
import type { EnvironmentRef, PrincipalRef } from '@soorma/policy-decision-seam';
import {
  createCachingAgentFacts,
  createEnvelopeAdmission,
  type AgentFacts,
  type AgentFactsSource,
  type CheckedAgentContext,
  type EnvelopeAdmission,
  type EnvelopeRefusedEvent,
  type EnvelopeRequest,
} from '../src/index.ts';

const testKey = (start: number): Buffer =>
  Buffer.from(Array.from({ length: 32 }, (_, i) => (start + i) & 0xff));

export const E: EnvironmentRef = { organization: 'o1', project: 'p1', environment: 'e' };
export const E2: EnvironmentRef = { organization: 'o1', project: 'p1', environment: 'e2' };
export const ringE = loadSealKeyRing({ current: 'k1', keys: [{ id: 'k1', key: testKey(0x60) }] });
export const ringE2 = loadSealKeyRing({ current: 'k1', keys: [{ id: 'k1', key: testKey(0x90) }] });
export const sealerE: Sealer = createSealer(ringE);
export const sealerE2: Sealer = createSealer(ringE2);

export const TRACEPARENT = '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01';
export const BOUND_MS = 60_000;

export interface AgentSpec {
  autonomy?: boolean;
  standing?: string[];
  declared?: string[];
}

export function agentFacts(spec: AgentSpec): AgentFacts {
  return {
    registrationView: {
      autonomyDeclared: spec.autonomy ?? true,
      reBroadeningDeclaration: new Set(spec.declared ?? []),
    },
    standingSet: new Set(spec.standing ?? []),
  };
}

/** facts: the in-memory agent-facts source, with a call counter, a failure, and a gate. */
export class Facts implements AgentFactsSource {
  readonly calls: { environment: EnvironmentRef; agents: string[] }[] = [];
  readonly table = new Map<string, AgentFacts>();
  failing = false;
  /** When set, a load waits for it before answering. */
  gate: Promise<void> | undefined;
  /** Called when a load starts, before it waits. */
  onLoad: (() => void) | undefined;

  constructor(agents: Record<string, AgentSpec> = {}) {
    for (const [agent, spec] of Object.entries(agents)) this.set(agent, spec);
  }

  set(agent: string, spec: AgentSpec): void {
    this.table.set(agent, agentFacts(spec));
  }

  async load(
    environment: EnvironmentRef,
    agents: readonly string[],
  ): Promise<ReadonlyMap<string, AgentFacts>> {
    this.calls.push({ environment, agents: [...agents] });
    const failing = this.failing;
    this.onLoad?.();
    if (this.gate) await this.gate;
    if (failing) throw new Error('store down');
    return new Map(
      agents.flatMap((a) => (this.table.has(a) ? [[a, this.table.get(a)!] as const] : [])),
    );
  }
}

export class TestClock {
  t = 0;
  now(): number {
    return this.t;
  }
}

export class CollectingLog {
  readonly events: EnvelopeRefusedEvent[] = [];
  envelopeRefused(event: EnvelopeRefusedEvent): void {
    this.events.push(event);
  }
}

export interface Admission {
  admission: EnvelopeAdmission;
  facts: Facts;
  clock: TestClock;
  log: CollectingLog;
}

/** admission(E): accepted {0.1.0}, E's scope, ring(E), the cached facts, P11, humans. */
export function admissionE(
  agents: Record<string, AgentSpec> = {},
  humans: readonly (readonly [PrincipalRef, string[]])[] = [],
): Admission {
  const facts = new Facts(agents);
  const clock = new TestClock();
  const log = new CollectingLog();
  const admission = createEnvelopeAdmission({
    acceptedVersions: ['0.1.0'],
    scope: E,
    keyRing: ringE,
    facts: createCachingAgentFacts(facts, { ttl: BOUND_MS, clock }),
    policyFactory: createPolicyDecision,
    humanGrants: inMemoryGrantSource(humans),
    securityLog: log,
  });
  return { admission, facts, clock, log };
}

export const context = (agent: string, scope: EnvironmentRef = E): CheckedAgentContext => ({
  scope,
  agent,
  instance: `${agent}-i`,
});

export function draft(extra: Record<string, unknown> = {}): Record<string, unknown> {
  return { clientContractVersion: '0.1.0', traceContext: { traceparent: TRACEPARENT }, ...extra };
}

export function request(
  agent: string,
  body: unknown = draft(),
  options: {
    required?: string[];
    header?: string[];
    requestId?: string;
    scope?: EnvironmentRef;
  } = {},
): EnvelopeRequest {
  return {
    body,
    contractVersionHeader: options.header ?? [],
    agent: context(agent, options.scope),
    required: options.required ?? ['event:publish'],
    requestId: options.requestId ?? 'r-1',
  };
}

/** An envelope as admission(E) would stamp one, for a chain of agents. */
export function envelope(
  chain: string[],
  extra: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    envelopeVersion: 1,
    scope: { ...E },
    originMode: 'autonomous',
    actorChain: chain.map((agent) => ({ agent, instance: `${agent}-i` })),
    traceContext: { traceparent: TRACEPARENT },
    ...extra,
  };
}

/** sealed(env, ...): inbound for a draft, sealed under a ring's current key. */
export function sealed(
  env: Record<string, unknown>,
  sealer: Sealer = sealerE,
): { envelope: Record<string, unknown>; seal: string } {
  return { envelope: env, seal: sealer.seal(canonicalize(env).bytes) };
}

/** Pads an envelope with an unknown field so its JCS form is `size` bytes. */
export function padTo(env: Record<string, unknown>, size: number): Record<string, unknown> {
  const base = canonicalize({ ...env, 'x-pad': '' }).bytes.length;
  return { ...env, 'x-pad': 'p'.repeat(size - base) };
}
