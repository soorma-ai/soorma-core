// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-AE-040: the latency of check-order steps 5 to 10, measured and REPORTED,
// never a gate (NFR-AE-07; P-NFR-05; D-CG-AE-08). Run at Build and Test with
// `pnpm bench:admit`; never in `pnpm test` or CI. Build and Test records p50
// and p99 against the target of 2 ms p99 on the reference workstation. There
// is no assertion on time.
//
// The input is a maximum-size forwarding draft: a sealed forwarded envelope
// with a 31-entry chain (so the stamped chain has 32), padded with an unknown
// field so the stamped envelope is just under 16384 bytes, and a traceContext
// whose tracestate is 512 characters. The agent-facts cache is warm, so no
// term read is timed (NFR-AE-07 excludes them).
import { canonicalize } from '@soorma/jcs';
import { test } from 'vitest';
import {
  admissionE,
  draft,
  envelope,
  padTo,
  request,
  sealed,
  TRACEPARENT,
} from '../test/support.ts';

const chain = Array.from({ length: 31 }, (_, i) => `agent-${i}`);
const agents = Object.fromEntries([...chain, 'b'].map((a) => [a, { standing: ['event:publish'] }]));
const { admission } = admissionE(agents);

const tracestate = Array.from({ length: 32 }, (_, i) => `k${i}=${'v'.repeat(10)}`)
  .join(',')
  .padEnd(512, 'v')
  .slice(0, 512);
// Pad the forwarded envelope so the STAMPED one (b's hop appended, the
// draft's trace context) lands 16 bytes under the bound.
const base = envelope(chain);
const stampedShape = {
  ...base,
  actorChain: [...(base.actorChain as unknown[]), { agent: 'b', instance: 'b-i' }],
  traceContext: { traceparent: TRACEPARENT, tracestate },
};
const forwarded = { ...base, 'x-pad': padTo(stampedShape, 16384 - 16)['x-pad'] };
const body = draft({
  traceContext: { traceparent: TRACEPARENT, tracestate },
  inbound: sealed(forwarded),
});
const req = request('b', body);

// Warm the cache, and check the input is what the case says.
const warm = await admission.admit(req);
if (!('admitted' in warm))
  throw new Error(`the benchmark input is refused: ${JSON.stringify(warm)}`);
const size = canonicalize(warm.admitted.envelope).bytes.length;
if (size !== 16384 - 16) throw new Error(`stamped size ${size} is not just under the bound`);
if ((warm.admitted.envelope.actorChain as unknown[]).length !== 32)
  throw new Error('the chain is not 32');

// Vitest 5's benchmark API is on the test context. The latency statistics
// come back from run(); they are printed, never asserted.
test('TC-AE-040: steps 5 to 10, maximum-size forwarding draft, warm cache (reported, not a gate)', async ({
  bench,
  annotate,
}) => {
  const result = await bench('admit', async () => {
    await admission.admit(req);
  }).run({ time: 2000, warmupTime: 500 });
  const ms = (n: number): string => n.toFixed(3);
  const report =
    `admit, steps 5 to 10: p50 ${ms(result.latency.p50)} ms, p99 ${ms(result.latency.p99)} ms, ` +
    `samples ${result.latency.samplesCount} (target: p99 <= 2 ms; reported, not a gate)`;
  console.log(report);
  await annotate(report);
});
