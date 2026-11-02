# Unit ↔ Story Map: soorma-core M1

Stories: [stories.md](../user-stories/stories.md). Units: [unit-of-work.md](unit-of-work.md).
**Primary** is the unit that delivers the story's surface. **Contributing** units build
parts the story exercises.

| Story | Primary unit | Contributing units | Done when |
|---|---|---|---|
| US-01 Deployer configures | U2 (organization config; `ensureFirstAdmin`) | U4 (environment config; first grant) | 1 |
| US-02 First Admin activates and signs in | U2 | — | 1 |
| US-03 Environment credential | U4 | U2 (verify-only material) | 1 |
| US-04 Self-grant | U4 | U3 (P3, extended by U4) | 1 |
| US-05 Register A and B | U5 | U4 (`evaluateHuman`, grants, held set), U3 | **1** |
| US-06 Issue secrets | U5 | U4 | 1 |
| US-07 Bootstrap and renew | U6 | U5 (registrations, secrets), U4 (P5 primitives) | **2** |
| US-08 A publishes, B receives | U7 | U3 (origin, O12, evaluation), U6 (credentials, revocation read), U5 | **3** |
| US-09 B's envelope | U7 | U3 (envelope, re-broadening; constructed-chain tests) | **4** |
| US-10 Cross-environment denial | U7 | U6 (credential verification per environment), U4 (human credential in E2) | **6** |
| US-11 Stamped field rejected | U7 | U3 (`validateDraft`) | **7** |
| US-12 Logout and material change | U2 (sign-in, material) | U4 (environment credential end) | — (SECURITY-12) |

## Units → Stories

| Unit | Primary | Contributing |
|---|---|---|
| U1 wire-contract | — | All (the contract every surface uses) |
| U2 org-identity | US-01, US-02, US-12 | US-03 |
| U3 authority-evaluation | — | US-04, US-05, US-08, US-09, US-11 |
| U4 env-human-access | US-03, US-04 | US-01, US-05, US-06, US-07, US-10, US-12 |
| U5 agent-registration | US-05, US-06 | US-07, US-08 |
| U6 agent-credentials | US-07 | US-08, US-10 |
| U7 event-transport | US-08, US-09, US-10, US-11 | — |

**Every story is assigned**, and every unit except U1 and U3 is the primary unit of at
least one story. U1 and U3 are contract and mechanism units, verified through the stories
of their consumers, and U3 directly at the authority-evaluation level (US-09).
