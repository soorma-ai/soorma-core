// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The verify-key cache (NP-EHA-03; NFR-EHA-08, 08a; U2 F-1, R-1): one per S2
// instance, holding the organization level's verify keys.
//
// - Start-up: the first fetch starts without blocking; issuance is
//   unavailable until a fetch succeeds (BR-IS-02), and nothing else waits
// - Schedule: a refresh every 5 minutes, from the injected timers
// - Single flight: at most one fetch in progress; a caller needing a fetch
//   while one runs awaits that one
// - On demand: an unknown kid, or no key held, triggers one fetch, at most one
//   per 30 seconds per instance. The limit counts on-demand fetches only: a
//   scheduled refresh neither waits for it nor resets it
// - Replacement: only by a well-formed JWKS (the S1 caller checks it); keys
//   are dropped only by such a replacement, so a failed fetch keeps the keys
//   held (and logs orglevel.unavailable)
// - It is the key source P1 reads on every verification (NP-EHA-15): nothing
//   holds a copy of the set, so a refresh is seen by the next verification
//
// With S1's signing-key rotation, step 2 waits at least 5 minutes, which covers
// the normal case; the on-demand fetch covers a refresh that failed during
// step 1's restart of S1, or ran late. "No valid sign-in is refused during a
// rotation" depends on both (NFR Requirements §3).
import type { KeyObject } from 'node:crypto';
import { globalTimers, type Clock, type SignInKeySource, type Timers } from '@soorma/service-kit';
import type { SecurityLog } from './security-log.ts';
import { KEY_REFETCH_LIMIT_MS, KEY_REFRESH_MS } from './settings.ts';

export interface VerifyKeyCacheOptions {
  fetch: () => Promise<Map<string, KeyObject>>;
  clock: Clock;
  log: SecurityLog;
  timers?: Timers;
  refreshMs?: number;
  refetchLimitMs?: number;
}

export class VerifyKeyCache implements SignInKeySource {
  private readonly options: VerifyKeyCacheOptions;
  private readonly timers: Timers;
  private keys = new Map<string, KeyObject>();
  private inflight: Promise<void> | undefined;
  private lastOnDemand = Number.NEGATIVE_INFINITY;
  private timer: unknown;
  private running = false;
  /** Fetches started, for tests and diagnostics. */
  fetches = 0;

  constructor(options: VerifyKeyCacheOptions) {
    this.options = options;
    this.timers = options.timers ?? globalTimers;
  }

  verifyKey(kid: string): KeyObject | undefined {
    return this.keys.get(kid);
  }

  hasKeys(): boolean {
    return this.keys.size > 0;
  }

  /** Starts the first fetch, without waiting for it, and the schedule. */
  start(): void {
    this.running = true;
    void this.fetch();
    this.schedule();
  }

  stop(): void {
    this.running = false;
    if (this.timer !== undefined) this.timers.clear(this.timer);
    this.timer = undefined;
  }

  /**
   * The on-demand fetch P1 calls on an unknown kid: joins a fetch in
   * progress; otherwise fetches, at most once per 30 seconds.
   */
  readonly refetch = async (): Promise<void> => {
    if (this.inflight) return this.inflight;
    const now = this.options.clock.now().getTime();
    if (now - this.lastOnDemand < (this.options.refetchLimitMs ?? KEY_REFETCH_LIMIT_MS)) return;
    this.lastOnDemand = now;
    return this.fetch();
  };

  /** One fetch, single flight. A failure keeps the keys held. */
  fetch(): Promise<void> {
    if (this.inflight) return this.inflight;
    this.fetches += 1;
    this.inflight = (async () => {
      try {
        this.keys = await this.options.fetch();
      } catch {
        this.options.log.event('orglevel.unavailable', undefined, { code: 'verify_keys' });
      } finally {
        this.inflight = undefined;
      }
    })();
    return this.inflight;
  }

  private schedule(): void {
    this.timer = this.timers.set(() => {
      if (!this.running) return;
      void this.fetch().finally(() => {
        if (this.running) this.schedule();
      });
    }, this.options.refreshMs ?? KEY_REFRESH_MS);
  }
}
