// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The local stack's certificates under strict X.509 verification (#36):
// every leaf stack-certs.ts issues carries a Subject and an Authority Key
// Identifier, so it verifies under `openssl verify -x509_strict`, and a
// Python 3.13+ client with ssl.create_default_context(), which sets
// VERIFY_X509_STRICT, completes a handshake against it.
//
// The handshake needs Python 3.13 or later. It is looked up on PATH and in
// the GitHub runner's tool cache (RUNNER_TOOL_CACHE, which carries 3.13 and
// later on ubuntu-24.04 without a setup step). Locally it is skipped when no
// such Python exists; in CI a missing one fails the test, so the coverage
// never disappears silently.
import { execFile, execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createServer, type Server } from 'node:tls';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { CA_CERT, ensureCertificates, LEAVES } from '../local/scripts/stack-certs.ts';

const run = promisify(execFile);
const PEM_BLOCK = /-----BEGIN ([A-Z ]+)-----[\s\S]+?-----END \1-----\n?/g;

/** A service secret's PEM blocks: its private key and its certificate. */
function split(pem: string): { key: string; cert: string } {
  const blocks = [...pem.matchAll(PEM_BLOCK)];
  const key = blocks.find((b) => b[1]!.endsWith('PRIVATE KEY'))?.[0];
  const cert = blocks.find((b) => b[1] === 'CERTIFICATE')?.[0];
  if (!key || !cert) throw new Error('expected a private key and a certificate');
  return { key, cert };
}

/** The first Python 3.13 or later on PATH or in the runner's tool cache. */
function strictPython(): string | undefined {
  const candidates = ['python3.15', 'python3.14', 'python3.13', 'python3'];
  const cache = process.env.RUNNER_TOOL_CACHE;
  if (cache && existsSync(join(cache, 'Python')))
    for (const version of readdirSync(join(cache, 'Python')).sort().reverse())
      candidates.push(join(cache, 'Python', version, 'x64', 'bin', 'python3'));
  for (const python of candidates) {
    try {
      const out = execFileSync(python, ['-I', '-c', 'import sys; print(*sys.version_info[:2])'], {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      });
      const [major, minor] = out.trim().split(' ').map(Number);
      if (major === 3 && minor! >= 13) return python;
    } catch {
      // Not installed, or not runnable: try the next.
    }
  }
  return undefined;
}

// The client: Python's default context, the stack CA, and the leaf's name.
const HANDSHAKE = `
import socket, ssl, sys
ctx = ssl.create_default_context(cafile=sys.argv[1])
assert ctx.verify_flags & ssl.VERIFY_X509_STRICT, "the default context lacks VERIFY_X509_STRICT"
with socket.create_connection(("127.0.0.1", int(sys.argv[2])), timeout=10) as raw:
    with ctx.wrap_socket(raw, server_hostname="localhost") as tls:
        print(tls.version(), "%d.%d" % sys.version_info[:2])
`;

describe('#36: the stack certificates verify strictly', () => {
  let dir: string;
  beforeAll(() => {
    dir = mkdtempSync(join(tmpdir(), 'soorma-certs-test-'));
    ensureCertificates({ reissue: true, dir });
  });
  afterAll(() => rmSync(dir, { recursive: true, force: true }));

  it('openssl verify -x509_strict accepts every leaf against the stack CA', () => {
    for (const leaf of LEAVES) {
      const certFile = join(dir, `${leaf.secret}.crt`);
      writeFileSync(certFile, split(readFileSync(join(dir, leaf.secret), 'utf8')).cert);
      let out: string;
      try {
        out = execFileSync(
          'openssl',
          ['verify', '-x509_strict', '-CAfile', join(dir, CA_CERT), certFile],
          {
            encoding: 'utf8',
            stdio: ['ignore', 'pipe', 'pipe'],
          },
        );
      } catch (error) {
        const e = error as { stdout?: string; stderr?: string };
        out = `${e.stdout ?? ''}${e.stderr ?? ''}`;
      }
      expect(out.trim(), leaf.secret).toBe(`${certFile}: OK`);
    }
  });

  const python = strictPython();
  it.skipIf(!python && !process.env.CI)(
    'a Python 3.13+ client with ssl.create_default_context() completes a handshake',
    async () => {
      expect(python, 'no Python 3.13 or later on PATH or in RUNNER_TOOL_CACHE').toBeDefined();
      const leaf = LEAVES.find(
        (l) => l.names.includes('localhost') && l.ips.includes('127.0.0.1'),
      )!;
      const server: Server = createServer(
        split(readFileSync(join(dir, leaf.secret), 'utf8')),
        (s) => s.end(),
      );
      await new Promise<void>((ok) => server.listen(0, '127.0.0.1', ok));
      try {
        const { port } = server.address() as { port: number };
        const { stdout } = await run(
          python!,
          ['-I', '-c', HANDSHAKE, join(dir, CA_CERT), String(port)],
          { timeout: 20_000 },
        ).catch((error: Error & { stderr?: string }) => {
          throw new Error(`the Python handshake failed: ${error.stderr ?? error.message}`);
        });
        expect(stdout.trim()).toMatch(/^TLSv1\.[23] 3\.(1[3-9]|[2-9]\d)$/);
      } finally {
        await new Promise((ok) => server.close(ok));
      }
    },
  );
});
