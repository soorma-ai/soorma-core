# End-to-End Test Instructions

The slice brief's *done when* items that soorma-core proves (1, 4, 6, 7, and 2 and 3 **with raw
calls and no SDK**), on the running stack. PF FR-023 requires identical enforcement for a tenant who
never links the SDK, so every call is a raw HTTPS request through
`deploy/local/scripts/stack-client.ts`: no SDK, no client library.

## Run

On a fresh stack, with the workspace built:

```bash
docker compose -f deploy/local/compose.yaml down -v
pnpm stack:up
pnpm test:e2e      # SOORMA_E2E=1, one file at a time (--no-file-parallelism)
```

One file at a time, because U5's backup round trip empties and restores E's store mid-run, and H's
first authentication happens once per stack, in `e2e/agent-registration.test.ts`.

## The journey (`e2e/agent-registration.test.ts`, in order)

Each step chains from the one before: the agents, secrets, and credentials are the real ones the
earlier steps made. Nothing in the *done when* proofs is seeded.

| Step | *Done when* | Test | What it shows |
|---|---|---|---|
| 1 | **1** | TC-AR-008 | H's first authentication, a sign-in, E's credential; H self-grants `agent:register`, `event:publish`, `event:subscribe`; registers A (`event:publish`) and B (`event:subscribe`), each with sponsor `h@example.com` and the ceiling snapshot of H's held set; issues one secret each; two `registerAgent` attribution records |
| 2 | **2** | TC-AC-093 | An instance of A and one of B bootstrap at E's S3 with those secrets and renew, raw calls |
| 3 | **3** | TC-ET-001 | B subscribes at E's S4; A publishes; B's stream carries A's Delivery |
| 4 | **4** | TC-ET-002, 003, 004 | The envelope B receives carries E's scope, origin `autonomous`, and the actor chain `[{ agent: A, instance: a-1 }]` stamped by S4 (the draft carried none), and the draft's `traceContext` unchanged; the publish's attribution record carries the same origin |
| 5 | **6** | TC-ET-006 | A credential of E2 publishes nothing at E, and E's nothing at E2: each 401 `credential_refused`, and B's stream receives nothing |
| 6 | **7** | TC-ET-007 | A draft that sets a platform-stamped field (each one in turn, `originMode` and `actorChain` among them) is refused 400 `stamped_field_set`, its pointer naming the field, and B's stream receives nothing |
| 7 | — | TC-AR-043, 044 | Every registration refusal holds for a raw call; the same credential from inside network `e` registers with the same sponsor (I3) |
| 8 | — | TC-AR-059, 056, 060 | Back up `e`, empty its store, restore; the registrations survive |

*Done when* 5 (a trace emitted) is soorma-sdk's. soorma-core carries `traceContext` on the envelope
(TC-ET-002's envelope, TC-WC-015), which is all the brief assigns it.

## U6's and U7's own e2e files

`e2e/agent-credentials.test.ts` (5 tests): no envelope on bootstrap or renewal, both attributed to
the agent with sponsor H (TC-AC-004, 005); revocation at either granularity at S3 (TC-AC-009, 025,
028); E's credential and secret refused at E2's S3 (TC-AC-013).

`e2e/event-transport.test.ts` (13 tests): payload numbers delivered exactly (TC-ET-071, 072);
live only (TC-ET-018); forwarding at B's hop with unknown fields kept (TC-ET-005, 020, 023);
two instances of one name each hold a stream (TC-ET-048); no autonomy declared is forbidden
(TC-ET-009); nothing crosses environments (TC-ET-015, 039, 090); a publish leaves its record and
nothing of the event (TC-ET-037); every refusal a Problem (TC-ET-040); the same credential from
inside network `e` (TC-ET-041); revocation reaches a publish and an open stream within B, at either
granularity (TC-ET-014, 017, 028, 031).

These seed registrations as the store's owner where a case is not a *done when* proof (U6's
`e2e/agent-credentials-support.ts`, U7's `e2e/event-transport-support.ts`): test-only, never in
an image.

## Result (2026-11-13)

**27 of 27 passed** on a fresh stack (`e2e/agent-registration.test.ts` 9, `agent-credentials` 5,
`event-transport` 13; 119 s). Every *done when* item soorma-core proves passes; see the summary's
*Proves* table.
