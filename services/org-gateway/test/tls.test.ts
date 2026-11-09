// SPDX-License-Identifier: FSL-1.1-ALv2
// A real TLS listener: the edge serves TLS 1.3 only, from one PEM file
// holding the key and the certificate (Infrastructure Design §4; the
// in-process half of TC-OI-056, whose stack half runs in the smoke test).
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { request } from 'node:https';
import type { AddressInfo } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { TLSSocket } from 'node:tls';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testDatabase,
  type TestDatabase,
} from '../../../packages/org-identity/test/harness/database.ts';
import { createEdgeApp } from '../src/apps.ts';
import { gateway, type Gateway } from './support.ts';

let db: TestDatabase;
let g: Gateway;
let dir: string;
beforeAll(async () => {
  db = await testDatabase();
  g = await gateway(db);
  dir = mkdtempSync(join(tmpdir(), 'soorma-tls-'));
  execFileSync(
    'openssl',
    [
      'req',
      '-x509',
      '-newkey',
      'ec',
      '-pkeyopt',
      'ec_paramgen_curve:P-256',
      '-nodes',
      '-keyout',
      join(dir, 'key.pem'),
      '-out',
      join(dir, 'cert.pem'),
      '-days',
      '1',
      '-subj',
      '/CN=localhost',
      '-addext',
      'subjectAltName=DNS:localhost,IP:127.0.0.1',
    ],
    { stdio: 'ignore' },
  );
});
afterAll(async () => {
  await g?.close();
  await db?.drop();
  rmSync(dir, { recursive: true, force: true });
});

function call(
  port: number,
  ca: Buffer,
  options: { maxVersion?: 'TLSv1.2' | 'TLSv1.3' } = {},
): Promise<{ status: number; protocol: string | null }> {
  return new Promise((resolve, reject) => {
    const req = request(
      {
        host: '127.0.0.1',
        servername: 'localhost',
        port,
        path: '/sign-ins',
        method: 'POST',
        ca,
        agent: false,
        ...options,
        headers: { 'content-type': 'application/json', 'soorma-contract-version': '0.1.0' },
      },
      (res) => {
        const protocol = (res.socket as TLSSocket).getProtocol();
        res.resume();
        res.on('end', () => resolve({ status: res.statusCode ?? 0, protocol }));
      },
    );
    req.on('error', reject);
    req.end('{}');
  });
}

describe('the edge over TLS', () => {
  it('serves TLS 1.3, verified against the CA, and refuses TLS 1.2', async () => {
    const key = readFileSync(join(dir, 'key.pem'));
    const cert = readFileSync(join(dir, 'cert.pem'));
    const app = await createEdgeApp(g.runtime, { pem: Buffer.concat([key, cert]) });
    await app.listen(0, '127.0.0.1');
    try {
      const { port } = app.getHttpServer().address() as AddressInfo;
      const ok = await call(port, cert);
      expect(ok).toEqual({ status: 400, protocol: 'TLSv1.3' });
      await expect(call(port, cert, { maxVersion: 'TLSv1.2' })).rejects.toThrow();
      await expect(call(port, Buffer.from(''))).rejects.toThrow();
    } finally {
      await app.close();
    }
  });
});
