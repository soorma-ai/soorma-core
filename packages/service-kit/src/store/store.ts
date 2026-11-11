// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Store access (P-15; NFR-OI-17): a pg Pool of at most 10 connections, a
// 5-second statement timeout, and a 2-second connection timeout, connected as
// the app role only. Parameterized SQL only: every statement is a constant
// from this package's sql.ts (D-CG-OI-04). A store error fails closed as
// `unavailable` (503); a constraint violation the caller expects is surfaced
// as ConflictError so it can decide.
import pg from 'pg';
import { UnavailableError } from '../errors.ts';
import { SQL, type Statement } from '../sql.ts';

export interface ConnectionSettings {
  host: string;
  port: number;
  database: string;
  user: string;
  password: string;
  /** The CA certificate; TLS with verify-full. Absent only for the test harness (D-CG-OI-15). */
  ca?: Buffer;
}

export const POOL_MAX = 10;
export const STATEMENT_TIMEOUT_MS = 5000;
export const CONNECTION_TIMEOUT_MS = 2000;

export function poolConfig(settings: ConnectionSettings): pg.PoolConfig {
  return {
    host: settings.host,
    port: settings.port,
    database: settings.database,
    user: settings.user,
    password: settings.password,
    max: POOL_MAX,
    connectionTimeoutMillis: CONNECTION_TIMEOUT_MS,
    statement_timeout: STATEMENT_TIMEOUT_MS,
    ...(settings.ca
      ? {
          ssl: {
            ca: settings.ca,
            rejectUnauthorized: true,
            servername: settings.host,
            minVersion: 'TLSv1.3' as const,
          },
        }
      : {}),
  };
}

/** A unique or check violation the caller handles (for example, single use lost to a race). */
export class ConflictError extends Error {
  readonly constraint: string | undefined;

  constructor(constraint: string | undefined) {
    super(`store conflict${constraint ? ` on ${constraint}` : ''}`);
    this.name = 'ConflictError';
    this.constraint = constraint;
  }
}

const CONFLICT_CODES = new Set(['23505', '23514', '23P01']);

function mapError(error: unknown, name: string | undefined): Error {
  const e = error as { code?: unknown; constraint?: unknown };
  if (typeof e.code === 'string' && CONFLICT_CODES.has(e.code))
    return new ConflictError(typeof e.constraint === 'string' ? e.constraint : undefined);
  const store = name === undefined ? 'the store' : `the ${name} store`;
  return new UnavailableError(`${store} cannot be reached or refused the statement`);
}

/** How a store is named in its errors: `org` for the org store, `env` for an environment's. */
export interface StoreOptions {
  name?: string;
}

export interface Queryable {
  query<R extends pg.QueryResultRow>(statement: Statement, params?: unknown[]): Promise<R[]>;
}

class ClientQueries implements Queryable {
  private readonly client: pg.PoolClient;
  private readonly name: string | undefined;

  constructor(client: pg.PoolClient, name: string | undefined) {
    this.client = client;
    this.name = name;
  }

  async query<R extends pg.QueryResultRow>(
    statement: Statement,
    params: unknown[] = [],
  ): Promise<R[]> {
    try {
      return (await this.client.query<R>(statement, params)).rows;
    } catch (error) {
      throw mapError(error, this.name);
    }
  }
}

export class Store implements Queryable {
  readonly pool: pg.Pool;
  private readonly name: string | undefined;

  constructor(pool: pg.Pool, options: StoreOptions = {}) {
    this.pool = pool;
    this.name = options.name;
  }

  static connect(settings: ConnectionSettings, options: StoreOptions = {}): Store {
    const pool = new pg.Pool(poolConfig(settings));
    // An idle client's error (the server went away) must not crash the process.
    pool.on('error', () => undefined);
    return new Store(pool, options);
  }

  async query<R extends pg.QueryResultRow>(
    statement: Statement,
    params: unknown[] = [],
  ): Promise<R[]> {
    try {
      return (await this.pool.query<R>(statement, params)).rows;
    } catch (error) {
      throw mapError(error, this.name);
    }
  }

  /** Runs `work` in one transaction (P-13): every multi-record change commits whole, or not at all. */
  async transaction<T>(work: (tx: Queryable) => Promise<T>): Promise<T> {
    let client: pg.PoolClient;
    try {
      client = await this.pool.connect();
    } catch (error) {
      throw mapError(error, this.name);
    }
    const tx = new ClientQueries(client, this.name);
    try {
      await tx.query(SQL.begin);
      const result = await work(tx);
      await tx.query(SQL.commit);
      return result;
    } catch (error) {
      await client.query(SQL.rollback).catch(() => undefined);
      throw error;
    } finally {
      client.release();
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}
