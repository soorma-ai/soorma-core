// SPDX-License-Identifier: FSL-1.1-ALv2
// Per-route body limits (U7 NP-ET-04): TC-ET-070. Without the option every
// path keeps 16 KiB, as before; service-kit's other tests are unchanged.
import { describe, expect, it } from 'vitest';
import { BODY_LIMIT, createAdapter } from '../src/http/index.ts';

async function post(routes: Record<string, number> | undefined, path: string, bytes: number) {
  const adapter = createAdapter(undefined, routes ? { routeBodyLimits: routes } : {});
  const fastify = adapter.getInstance();
  for (const p of ['/x', '/y']) fastify.post(p, () => Promise.resolve('ok'));
  await fastify.ready();
  try {
    const r = await fastify.inject({
      method: 'POST',
      url: path,
      headers: { 'content-type': 'application/json' },
      payload: Buffer.alloc(bytes, 0x20),
    });
    return r.statusCode;
  } finally {
    await fastify.close();
  }
}

describe('TC-ET-070: route body limits are additive', () => {
  it('a named route takes its own limit, at and over it', async () => {
    expect(await post({ '/x': 32_768 }, '/x', 32_768)).toBe(200);
    expect(await post({ '/x': 32_768 }, '/x', 32_769)).toBe(413);
  });

  it('every other path keeps 16 KiB', async () => {
    expect(BODY_LIMIT).toBe(16_384);
    expect(await post({ '/x': 32_768 }, '/y', 16_384)).toBe(200);
    expect(await post({ '/x': 32_768 }, '/y', 16_385)).toBe(413);
  });

  it('without the option, nothing changes', async () => {
    expect(await post(undefined, '/x', 16_384)).toBe(200);
    expect(await post(undefined, '/x', 16_385)).toBe(413);
  });
});
