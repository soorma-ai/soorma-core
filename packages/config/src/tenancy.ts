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
  internalCallers: { environment: string; publicKey: Buffer }[];
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
  internalCallers?: { environment: string; publicKey: string }[];
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

  const callers = (level.internalCallers ?? []).map((c) => c.environment);
  for (const env of duplicates(callers))
    problems.push(`/organizationLevel/internalCallers: environment ${env} appears twice`);
  for (const [i, env] of callers.entries()) {
    if (!environments.includes(env))
      problems.push(
        `/organizationLevel/internalCallers/${i}: environment ${env} is not configured`,
      );
  }

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
      publicKey: read.bytes(c.publicKey),
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
