// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P9, the organization half: loads tenancy.yaml, validates it, and reads the
// secrets the caller's role needs (BR-CFG-01 to 09; D-CG-OI-12).
//
// - Identity comes from this file only. Nothing here reads the host name, the
//   process environment, or anything else (BR-CFG-01; D-OI-09)
// - Any error stops start-up: loadOrganization throws, listing every problem
//   (BR-CFG-08). A message names a setting or a secret's name, never a secret's
//   content
// - Each role reads only its own secrets: org-migrate never reads S1's keys,
//   and S1 never reads the migrator password (D-ID-OI-02)
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { Ajv2020, type ErrorObject } from 'ajv/dist/2020.js';
import { parse as parseYaml } from 'yaml';

/** The secrets directory Compose mounts; tests pass their own. */
export const DEFAULT_SECRETS_DIR = '/run/secrets';

/** A symmetric key is at least 256 bits (P-02). */
const MIN_KEY_BYTES = 32;
const ENROLLMENT_MATERIAL = /^soorma_em_[A-Za-z0-9_-]+$/;
const BASE64URL = /^[A-Za-z0-9_-]+$/;

export class ConfigurationError extends Error {
  readonly problems: readonly string[];

  constructor(problems: readonly string[]) {
    super(`configuration refused (${problems.length}):\n- ${problems.join('\n- ')}`);
    this.name = 'ConfigurationError';
    this.problems = problems;
  }
}

export interface Environment {
  id: string;
  firstAdmin: string;
  /** The envelope-seal key ring (U3 NP-02); only S4 reads its secrets. */
  sealKeys?: SealKeyNames;
  /** The environment's S2 (U4 Infrastructure Design §3); only that S2 reads its secrets. */
  controlGateway?: ControlGatewayNames;
  /** The environment's S3 (U6 Infrastructure Design §6); only that S3 reads its secrets. */
  dataGateway?: DataGatewayNames;
}

/** An environment's S3 part as configured: settings, and secrets by name (D-ID-AC-10). */
export interface DataGatewayNames {
  edge: { port: number; tls: string };
  health: { port: number };
  database: {
    host: string;
    port: number;
    name: string;
    user: string;
    password: string;
    ca: string;
  };
  keys: { signing: string; verify: string[] };
  bound: { counter: string };
}

/**
 * S3's configuration, loaded for its own environment only (D-ID-AC-09, 10). It
 * holds no propagation bound and no lifetime: those are code constants
 * (NP-AC-01).
 */
export interface DataGatewayConfiguration {
  settings: {
    organization: string;
    project: string;
    environment: string;
    edge: { port: number };
    health: { port: number };
    database: { host: string; port: number; name: string; user: string };
  };
  secrets: {
    edgeTls: Buffer;
    databasePassword: string;
    databaseCa: Buffer;
    /** E's agent key ring, by name, in configuration order; `signing` names one (D-AC-03). */
    verifyKeys: { name: string; pem: Buffer }[];
    signing: string;
    /** The bound's HMAC key (D-ID-AC-06). */
    counterSecret: Buffer;
  };
}

/** An environment's S2 part as configured: settings, and secrets by name (U4 P-06). */
export interface ControlGatewayNames {
  edge: { port: number; tls: string };
  health: { port: number };
  database: {
    host: string;
    port: number;
    name: string;
    user: string;
    password: string;
    ca: string;
  };
  migrator: { user: string; password: string };
  keys: { signing: string; verify: string[]; caller: string; logPseudonym: string };
  organizationLevel: { host: string; port: number; ca: string };
}

/** S2's configuration, loaded for its own environment only (U4 P-06; BR-CFG). */
export interface ControlGatewayConfiguration {
  settings: {
    organization: string;
    project: string;
    environment: string;
    firstAdmin: string;
    edge: { port: number };
    health: { port: number };
    database: { host: string; port: number; name: string; user: string };
    organizationLevel: { host: string; port: number };
  };
  secrets: {
    edgeTls: Buffer;
    databasePassword: string;
    databaseCa: Buffer;
    /** E's key ring, by name, in configuration order; `signing` names one (NP-EHA-02). */
    verifyKeys: { name: string; pem: Buffer }[];
    signing: string;
    callerKey: Buffer;
    logPseudonymKey: Buffer;
    organizationCa: Buffer;
  };
}

/** {env}-migrate's configuration: its store, the migrator password, and the CA. */
export interface EnvironmentMigratorConfiguration {
  database: { host: string; port: number; name: string; user: string };
  databasePassword: string;
  databaseCa: Buffer;
}

/** An environment's seal keys as configured: the seed keys' shape (U3 NP-02). */
export interface SealKeyNames {
  current: string;
  keys: { id: string; secret: string }[];
}

/** An environment's seal keys, loaded: each key exactly 256 bits (U3 NP-02). */
export interface SealKeys {
  current: string;
  keys: { id: string; key: Buffer }[];
}

export interface Project {
  id: string;
  environments: Environment[];
}

/** A first Admin, once per principal, with the environment that names it first (BR-CFG-05). */
export interface FirstAdmin {
  principal: string;
  registeredBy: string;
}

export interface OrganizationSettings {
  organization: string;
  secondFactorRequired: boolean;
  projects: Project[];
  /** Every environment identifier, in configuration order. */
  environments: string[];
  /** Each first Admin once, in configuration order. */
  firstAdmins: FirstAdmin[];
  edge: { port: number };
  internal: { port: number };
  health: { port: number };
  database: { host: string; port: number; name: string; user: string };
  migrator: { user: string };
  hashing: { budgetMiB: number; permits?: number };
}

/** S1's secrets. Raw bytes and text: the key ring parses and brands them. */
export interface GatewaySecrets {
  edgeTls: Buffer;
  internalTls: Buffer;
  databasePassword: string;
  databaseCa: Buffer;
  signingKey: Buffer;
  verifyKeys: Buffer[];
  seedKeys: { current: string; keys: { id: string; key: Buffer }[] };
  counterSecret: Buffer;
  logPseudonymKey: Buffer;
  /** Configured enrollment material, keyed by principal (organization part only). */
  enrollment: { principal: string; material: string }[];
  internalCallers: { environment: string; publicKeys: Buffer[] }[];
}

/** org-migrate's secrets: the migrator password and the CA, nothing else. */
export interface MigratorSecrets {
  databasePassword: string;
  databaseCa: Buffer;
}

export interface LoadOptions {
  /** The path of tenancy.yaml. */
  configPath: string;
  /** The secrets directory; /run/secrets by default. */
  secretsDir?: string;
}

interface RawLevel {
  edge: { port: number; tls: string };
  internal: { port: number; tls: string };
  health: { port: number };
  database: {
    host: string;
    port: number;
    name: string;
    user: string;
    password: string;
    ca: string;
  };
  migrator: { user: string; password: string };
  keys: {
    signing: string;
    verify?: string[];
    seed: { current: string; keys: { id: string; secret: string }[] };
    counter: string;
    logPseudonym: string;
  };
  enrollment: { principal: string; secret: string }[];
  internalCallers?: { environment: string; publicKeys: string[] }[];
  hashing?: { budgetMiB?: number; permits?: number };
}

interface RawTenancy {
  organization: string;
  secondFactorRequired: boolean;
  organizationLevel: RawLevel;
  projects: Project[];
}

const schema = JSON.parse(
  readFileSync(new URL('../schema/tenancy.schema.json', import.meta.url), 'utf8'),
) as object;
const validateTenancy = new Ajv2020({ strict: true, allErrors: true }).compile<RawTenancy>(schema);

function schemaProblems(errors: ErrorObject[] | null | undefined): string[] {
  return (errors ?? []).map((e) => `${e.instancePath || '/'}: ${e.message ?? 'invalid'}`);
}

function duplicates(values: string[]): string[] {
  const seen = new Set<string>();
  const out = new Set<string>();
  for (const v of values) (seen.has(v) ? out : seen).add(v);
  return [...out];
}

function readTenancy(configPath: string): { raw: RawTenancy; settings: OrganizationSettings } {
  let data: unknown;
  try {
    data = parseYaml(readFileSync(configPath, 'utf8'));
  } catch (error) {
    const reason = error instanceof Error ? error.message.split('\n')[0] : 'unreadable';
    throw new ConfigurationError([`${configPath}: ${reason}`]);
  }
  if (!validateTenancy(data)) throw new ConfigurationError(schemaProblems(validateTenancy.errors));
  const raw = data;
  const level = raw.organizationLevel;
  const problems: string[] = [];

  for (const id of duplicates(raw.projects.map((p) => p.id)))
    problems.push(`/projects: project ${id} appears twice`);
  const environments = raw.projects.flatMap((p) => p.environments.map((e) => e.id));
  for (const id of duplicates(environments))
    problems.push(`/projects: environment ${id} appears twice`);

  const firstAdmins: FirstAdmin[] = [];
  for (const project of raw.projects) {
    for (const env of project.environments) {
      if (!firstAdmins.some((a) => a.principal === env.firstAdmin))
        firstAdmins.push({ principal: env.firstAdmin, registeredBy: env.id });
    }
  }

  const enrolled = level.enrollment.map((e) => e.principal);
  for (const p of duplicates(enrolled))
    problems.push(`/organizationLevel/enrollment: principal ${p} appears twice`);
  for (const [i, e] of level.enrollment.entries()) {
    if (!firstAdmins.some((a) => a.principal === e.principal))
      problems.push(
        `/organizationLevel/enrollment/${i}: no environment names this principal as first Admin`,
      );
  }

  const seedIds = level.keys.seed.keys.map((k) => k.id);
  for (const id of duplicates(seedIds))
    problems.push(`/organizationLevel/keys/seed: key id ${id} appears twice`);
  if (!seedIds.includes(level.keys.seed.current))
    problems.push('/organizationLevel/keys/seed/current: names no configured seed key');

  // Each environment's seal keys: checked as the seed keys are (U3 NP-02).
  for (const [pi, project] of raw.projects.entries()) {
    for (const [ei, env] of project.environments.entries()) {
      if (!env.sealKeys) continue;
      const at = `/projects/${pi}/environments/${ei}/sealKeys`;
      const ids = env.sealKeys.keys.map((k) => k.id);
      for (const id of duplicates(ids)) problems.push(`${at}: key id ${id} appears twice`);
      if (!ids.includes(env.sealKeys.current))
        problems.push(`${at}/current: names no configured seal key`);
    }
  }

  // Each environment's S2 part (U4 Infrastructure Design §3; ID §6): signing is
  // one of verify; no name twice in verify; no secret shared with another
  // environment's part, or with the organization level, other than the CA
  // certificate, which is public.
  const caNames = new Set<string>([level.database.ca]);
  const parts: { at: string; env: string; names: string[] }[] = [];
  for (const [pi, project] of raw.projects.entries()) {
    for (const [ei, env] of project.environments.entries()) {
      const cg = env.controlGateway;
      if (!cg) continue;
      const at = `/projects/${pi}/environments/${ei}/controlGateway`;
      for (const name of duplicates(cg.keys.verify))
        problems.push(`${at}/keys/verify: ${name} is listed twice`);
      if (!cg.keys.verify.includes(cg.keys.signing))
        problems.push(`${at}/keys/signing: names no verify key`);
      caNames.add(cg.database.ca);
      caNames.add(cg.organizationLevel.ca);
      parts.push({
        at,
        env: env.id,
        names: [
          ...new Set([
            cg.edge.tls,
            cg.database.password,
            cg.migrator.password,
            ...cg.keys.verify,
            cg.keys.caller,
            cg.keys.logPseudonym,
          ]),
        ],
      });
    }
  }
  // Each environment's S3 part (U6 D-ID-AC-07, 09, 10), checked as S2's, and
  // as its own owner: S3 shares no secret with its environment's S2 (the
  // separate agent ring, D-AC-03; its own data password), and never connects
  // as S2's role or the migrator.
  for (const [pi, project] of raw.projects.entries()) {
    for (const [ei, env] of project.environments.entries()) {
      const dg = env.dataGateway;
      if (!dg) continue;
      const at = `/projects/${pi}/environments/${ei}/dataGateway`;
      for (const name of duplicates(dg.keys.verify))
        problems.push(`${at}/keys/verify: ${name} is listed twice`);
      if (!dg.keys.verify.includes(dg.keys.signing))
        problems.push(`${at}/keys/signing: names no verify key`);
      const cg = env.controlGateway;
      if (cg && [cg.database.user, cg.migrator.user].includes(dg.database.user))
        problems.push(`${at}/database/user: ${dg.database.user} is not S3's own role`);
      caNames.add(dg.database.ca);
      parts.push({
        at,
        env: `${env.id} (dataGateway)`,
        names: [
          ...new Set([dg.edge.tls, dg.database.password, ...dg.keys.verify, dg.bound.counter]),
        ],
      });
    }
  }
  const organizationNames = new Set<string>([
    level.edge.tls,
    level.internal.tls,
    level.database.password,
    level.migrator.password,
    level.keys.signing,
    ...(level.keys.verify ?? []),
    ...level.keys.seed.keys.map((k) => k.secret),
    level.keys.counter,
    level.keys.logPseudonym,
    ...level.enrollment.map((e) => e.secret),
  ]);
  const owner = new Map<string, string>();
  for (const part of parts) {
    for (const name of part.names) {
      if (caNames.has(name)) continue;
      if (organizationNames.has(name))
        problems.push(`${part.at}: ${name} is an organization-level secret`);
      const other = owner.get(name);
      if (other !== undefined && other !== part.env)
        problems.push(`${part.at}: ${name} is also named by environment ${other}`);
      else owner.set(name, part.env);
    }
  }

  const callers = (level.internalCallers ?? []).map((c) => c.environment);
  for (const env of duplicates(callers))
    problems.push(`/organizationLevel/internalCallers: environment ${env} appears twice`);
  for (const [i, env] of callers.entries()) {
    if (!environments.includes(env))
      problems.push(
        `/organizationLevel/internalCallers/${i}: environment ${env} is not configured`,
      );
  }
  // A secret name names one key, for one environment (U4 Infrastructure Design §4; I1).
  const names = (level.internalCallers ?? []).flatMap((c) => c.publicKeys);
  const repeated = new Set(duplicates(names));
  for (const [i, c] of (level.internalCallers ?? []).entries())
    for (const [j, name] of c.publicKeys.entries())
      if (repeated.has(name))
        problems.push(
          `/organizationLevel/internalCallers/${i}/publicKeys/${j}: ${name} is listed more than once`,
        );

  if (problems.length > 0) throw new ConfigurationError(problems);

  return {
    raw,
    settings: {
      organization: raw.organization,
      secondFactorRequired: raw.secondFactorRequired,
      projects: raw.projects,
      environments,
      firstAdmins,
      edge: { port: level.edge.port },
      internal: { port: level.internal.port },
      health: { port: level.health.port },
      database: {
        host: level.database.host,
        port: level.database.port,
        name: level.database.name,
        user: level.database.user,
      },
      migrator: { user: level.migrator.user },
      hashing: {
        budgetMiB: level.hashing?.budgetMiB ?? 512,
        ...(level.hashing?.permits === undefined ? {} : { permits: level.hashing.permits }),
      },
    },
  };
}

/** Reads named secret files, collecting a problem for each one that is missing or empty. */
class SecretReader {
  readonly problems: string[] = [];
  private readonly dir: string;

  constructor(dir: string) {
    this.dir = dir;
  }

  bytes(name: string): Buffer {
    try {
      const value = readFileSync(join(this.dir, name));
      if (value.length === 0) this.problems.push(`secret ${name} is empty`);
      return value;
    } catch {
      this.problems.push(`secret ${name} cannot be read`);
      return Buffer.alloc(0);
    }
  }

  text(name: string): string {
    return this.bytes(name).toString('utf8').trim();
  }

  /** A symmetric key: base64url text of at least 256 bits; exactly 256 when `exact`. */
  key(name: string, exact = false): Buffer {
    const text = this.text(name);
    if (text.length === 0) return Buffer.alloc(0);
    if (!BASE64URL.test(text)) {
      this.problems.push(`secret ${name} is not base64url text`);
      return Buffer.alloc(0);
    }
    const key = Buffer.from(text, 'base64url');
    if (exact ? key.length !== MIN_KEY_BYTES : key.length < MIN_KEY_BYTES)
      this.problems.push(
        `secret ${name} must hold ${exact ? 'exactly' : 'at least'} ${MIN_KEY_BYTES * 8} bits`,
      );
    return key;
  }
}

/** Loads the settings only: no secret is read. */
export function loadSettings(options: LoadOptions): OrganizationSettings {
  return readTenancy(options.configPath).settings;
}

/** S1's configuration: the settings and S1's secrets. Never the migrator password. */
export function loadOrganization(options: LoadOptions): {
  settings: OrganizationSettings;
  secrets: GatewaySecrets;
} {
  const { raw, settings } = readTenancy(options.configPath);
  const level = raw.organizationLevel;
  const read = new SecretReader(options.secretsDir ?? DEFAULT_SECRETS_DIR);
  const secrets: GatewaySecrets = {
    edgeTls: read.bytes(level.edge.tls),
    internalTls: read.bytes(level.internal.tls),
    databasePassword: read.text(level.database.password),
    databaseCa: read.bytes(level.database.ca),
    signingKey: read.bytes(level.keys.signing),
    verifyKeys: (level.keys.verify ?? []).map((n) => read.bytes(n)),
    seedKeys: {
      current: level.keys.seed.current,
      keys: level.keys.seed.keys.map((k) => ({ id: k.id, key: read.key(k.secret, true) })),
    },
    counterSecret: read.key(level.keys.counter),
    logPseudonymKey: read.key(level.keys.logPseudonym),
    enrollment: level.enrollment.map((e) => {
      const material = read.text(e.secret);
      if (material.length > 0 && (material.length > 256 || !ENROLLMENT_MATERIAL.test(material)))
        read.problems.push(
          `secret ${e.secret} is not enrollment material (soorma_em_…, at most 256)`,
        );
      return { principal: e.principal, material };
    }),
    internalCallers: (level.internalCallers ?? []).map((c) => ({
      environment: c.environment,
      publicKeys: c.publicKeys.map((name) => read.bytes(name)),
    })),
  };
  if (secrets.counterSecret.length > 0 && secrets.counterSecret.equals(secrets.logPseudonymKey))
    read.problems.push('the log-pseudonym key must differ from the counter secret (NFR-OI-22)');
  if (read.problems.length > 0) throw new ConfigurationError(read.problems);
  return { settings, secrets };
}

/** org-migrate's configuration: the settings, the migrator password, and the CA. */
export function loadMigrator(options: LoadOptions): {
  settings: OrganizationSettings;
  secrets: MigratorSecrets;
} {
  const { raw, settings } = readTenancy(options.configPath);
  const level = raw.organizationLevel;
  const read = new SecretReader(options.secretsDir ?? DEFAULT_SECRETS_DIR);
  const secrets: MigratorSecrets = {
    databasePassword: read.text(level.migrator.password),
    databaseCa: read.bytes(level.database.ca),
  };
  if (read.problems.length > 0) throw new ConfigurationError(read.problems);
  return { settings, secrets };
}

/**
 * One environment's seal keys, for its event transport (S4) at start-up (U3
 * NP-02; D-CG-AE-06). Each key is read through the seed keys' path,
 * SecretReader.key(secret, true): base64url text of exactly 256 bits. Every
 * problem is collected, then start-up is refused. An unknown project or
 * environment, or one with no sealKeys, is refused. Reads no other secret.
 */
export function loadSealKeys(
  options: LoadOptions,
  where: { project: string; environment: string },
): SealKeys {
  const { raw } = readTenancy(options.configPath);
  const env = raw.projects
    .find((p) => p.id === where.project)
    ?.environments.find((e) => e.id === where.environment);
  if (!env)
    throw new ConfigurationError([
      `environment ${where.project}/${where.environment} is not configured`,
    ]);
  if (!env.sealKeys)
    throw new ConfigurationError([
      `environment ${where.project}/${where.environment} has no sealKeys`,
    ]);
  const read = new SecretReader(options.secretsDir ?? DEFAULT_SECRETS_DIR);
  const sealKeys: SealKeys = {
    current: env.sealKeys.current,
    keys: env.sealKeys.keys.map((k) => ({ id: k.id, key: read.key(k.secret, true) })),
  };
  if (read.problems.length > 0) throw new ConfigurationError(read.problems);
  return sealKeys;
}

function controlGatewayOf(
  raw: RawTenancy,
  where: { project: string; environment: string },
): { env: Environment; cg: ControlGatewayNames } {
  const env = raw.projects
    .find((p) => p.id === where.project)
    ?.environments.find((e) => e.id === where.environment);
  if (!env)
    throw new ConfigurationError([
      `environment ${where.project}/${where.environment} is not configured`,
    ]);
  if (!env.controlGateway)
    throw new ConfigurationError([
      `environment ${where.project}/${where.environment} has no controlGateway`,
    ]);
  return { env, cg: env.controlGateway };
}

/**
 * An environment's S2 configuration at start-up (U4 P-06). Reads only that
 * environment's part and its secrets, never the migrator password, and never
 * another environment's or the organization level's secret. Every problem is
 * collected, then start-up is refused (BR-CFG).
 */
export function loadControlGateway(
  options: LoadOptions,
  where: { project: string; environment: string },
): ControlGatewayConfiguration {
  const { raw } = readTenancy(options.configPath);
  const { env, cg } = controlGatewayOf(raw, where);
  const read = new SecretReader(options.secretsDir ?? DEFAULT_SECRETS_DIR);
  const secrets = {
    edgeTls: read.bytes(cg.edge.tls),
    databasePassword: read.text(cg.database.password),
    databaseCa: read.bytes(cg.database.ca),
    verifyKeys: cg.keys.verify.map((name) => ({ name, pem: read.bytes(name) })),
    signing: cg.keys.signing,
    callerKey: read.bytes(cg.keys.caller),
    logPseudonymKey: read.key(cg.keys.logPseudonym),
    organizationCa: read.bytes(cg.organizationLevel.ca),
  };
  if (read.problems.length > 0) throw new ConfigurationError(read.problems);
  return {
    settings: {
      organization: raw.organization,
      project: where.project,
      environment: env.id,
      firstAdmin: env.firstAdmin,
      edge: { port: cg.edge.port },
      health: { port: cg.health.port },
      database: {
        host: cg.database.host,
        port: cg.database.port,
        name: cg.database.name,
        user: cg.database.user,
      },
      organizationLevel: { host: cg.organizationLevel.host, port: cg.organizationLevel.port },
    },
    secrets,
  };
}

/**
 * An environment's S3 configuration at start-up (U6 D-ID-AC-09, 10). Reads only
 * that environment's S3 part and its secrets: never S2's, the migrator's,
 * another environment's, or the organization level's. Every problem is
 * collected, then start-up is refused (BR-CFG).
 */
export function loadDataGateway(
  options: LoadOptions,
  where: { project: string; environment: string },
): DataGatewayConfiguration {
  const { raw } = readTenancy(options.configPath);
  const env = raw.projects
    .find((p) => p.id === where.project)
    ?.environments.find((e) => e.id === where.environment);
  if (!env)
    throw new ConfigurationError([
      `environment ${where.project}/${where.environment} is not configured`,
    ]);
  const dg = env.dataGateway;
  if (!dg)
    throw new ConfigurationError([
      `environment ${where.project}/${where.environment} has no dataGateway`,
    ]);
  const read = new SecretReader(options.secretsDir ?? DEFAULT_SECRETS_DIR);
  const secrets = {
    edgeTls: read.bytes(dg.edge.tls),
    databasePassword: read.text(dg.database.password),
    databaseCa: read.bytes(dg.database.ca),
    verifyKeys: dg.keys.verify.map((name) => ({ name, pem: read.bytes(name) })),
    signing: dg.keys.signing,
    counterSecret: read.key(dg.bound.counter),
  };
  if (read.problems.length > 0) throw new ConfigurationError(read.problems);
  return {
    settings: {
      organization: raw.organization,
      project: where.project,
      environment: env.id,
      edge: { port: dg.edge.port },
      health: { port: dg.health.port },
      database: {
        host: dg.database.host,
        port: dg.database.port,
        name: dg.database.name,
        user: dg.database.user,
      },
    },
    secrets,
  };
}

/** {env}-migrate's configuration: the migrator password and the CA, nothing else. */
export function loadEnvironmentMigrator(
  options: LoadOptions,
  where: { project: string; environment: string },
): EnvironmentMigratorConfiguration {
  const { raw } = readTenancy(options.configPath);
  const { cg } = controlGatewayOf(raw, where);
  const read = new SecretReader(options.secretsDir ?? DEFAULT_SECRETS_DIR);
  const out = {
    database: {
      host: cg.database.host,
      port: cg.database.port,
      name: cg.database.name,
      user: cg.migrator.user,
    },
    databasePassword: read.text(cg.migrator.password),
    databaseCa: read.bytes(cg.database.ca),
  };
  if (read.problems.length > 0) throw new ConfigurationError(read.problems);
  return out;
}

/** The secret names a configuration references, by who reads them; for stack:init. */
export interface SecretNames {
  /** S1's secrets (never the migrator password). */
  gateway: string[];
  /** org-migrate's: the migrator password and the CA. */
  migrator: string[];
  /** Enrollment material, in configuration order, with its principal. */
  enrollment: { principal: string; secret: string }[];
  /** TLS secrets (a PEM holding a key and its certificate chain). */
  tls: string[];
  /** The CA certificate the clients verify against. */
  ca: string;
  /** The Ed25519 signing key. */
  signing: string;
  /** Each environment's S2 part (U4 P-06), for stack:init at Group 6. */
  environments: {
    project: string;
    environment: string;
    /** S2's secrets (never the migrator password). */
    controlGateway: string[];
    /** {env}-migrate's: the migrator password and the CA. */
    migrator: string[];
    tls: string;
    /** Ed25519 private keys: E's verify keys (signing among them) and its caller key. */
    ed25519: string[];
    /** The caller key (among `ed25519`), whose public half `callerPublic` holds. */
    caller: string;
    /** The caller keys' public halves, as S1's internalCallers names them. */
    callerPublic: string[];
    logPseudonym: string;
    databasePassword: string;
    migratorPassword: string;
    /** The environment's S3 part (U6 D-ID-AC-05, 06, 09), when configured. */
    dataGateway?: {
      /** S3's secrets: its data-gateway/ subdirectory. */
      secrets: string[];
      tls: string;
      /** E's agent ring: Ed25519 private keys, each with a derived verify half. */
      agentKeys: string[];
      /** The bound's counter secret (256 bits). */
      counter: string;
      /** soorma_env_data's password. */
      databasePassword: string;
    };
  }[];
}

export function listSecrets(options: LoadOptions): SecretNames {
  const { raw } = readTenancy(options.configPath);
  const level = raw.organizationLevel;
  const unique = (names: string[]): string[] => [...new Set(names)];
  const tls = unique([level.edge.tls, level.internal.tls]);
  return {
    gateway: unique([
      ...tls,
      level.database.password,
      level.database.ca,
      level.keys.signing,
      ...(level.keys.verify ?? []),
      ...level.keys.seed.keys.map((k) => k.secret),
      level.keys.counter,
      level.keys.logPseudonym,
      ...level.enrollment.map((e) => e.secret),
      ...(level.internalCallers ?? []).flatMap((c) => c.publicKeys),
    ]),
    migrator: unique([level.migrator.password, level.database.ca]),
    enrollment: level.enrollment.map((e) => ({ principal: e.principal, secret: e.secret })),
    tls,
    ca: level.database.ca,
    signing: level.keys.signing,
    environments: raw.projects.flatMap((p) =>
      p.environments.flatMap((e) => {
        const cg = e.controlGateway;
        if (!cg) return [];
        const callerPublic = (level.internalCallers ?? [])
          .filter((c) => c.environment === e.id)
          .flatMap((c) => c.publicKeys);
        return [
          {
            project: p.id,
            environment: e.id,
            controlGateway: unique([
              cg.edge.tls,
              cg.database.password,
              cg.database.ca,
              ...cg.keys.verify,
              cg.keys.caller,
              cg.keys.logPseudonym,
              cg.organizationLevel.ca,
            ]),
            migrator: unique([cg.migrator.password, cg.database.ca]),
            tls: cg.edge.tls,
            ed25519: unique([...cg.keys.verify, cg.keys.caller]),
            caller: cg.keys.caller,
            callerPublic,
            logPseudonym: cg.keys.logPseudonym,
            databasePassword: cg.database.password,
            migratorPassword: cg.migrator.password,
            ...(e.dataGateway
              ? {
                  dataGateway: {
                    secrets: unique([
                      e.dataGateway.edge.tls,
                      e.dataGateway.database.ca,
                      e.dataGateway.database.password,
                      ...e.dataGateway.keys.verify,
                      e.dataGateway.bound.counter,
                    ]),
                    tls: e.dataGateway.edge.tls,
                    agentKeys: unique(e.dataGateway.keys.verify),
                    counter: e.dataGateway.bound.counter,
                    databasePassword: e.dataGateway.database.password,
                  },
                }
              : {}),
          },
        ];
      }),
    ),
  };
}
