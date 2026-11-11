<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# `@soorma/attribution` (P7)

Attribution records: **one per state-changing operation**, written in the same transaction as
the write it records, by `recordAttribution(tx, record)`. A refused operation writes none.

The whole record shape is defined here, once, for every kind of actor:

| Actor           | Carries                                                                                                                                                            |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `human`         | The principal, and the credential presented: the sign-in at issuance, the environment credential otherwise. No chain, origin, or re-broadening                     |
| `configuration` | Nothing of a principal or a credential (the configured first grant)                                                                                                |
| `agent`         | Added by the agent units: the registration, the instance, the sponsor as of the write, and, with an envelope, its stamped chain, origin, and re-broadening outcome |

`checkRecord` refuses an inconsistent record before any SQL, raising `AttributionRecordError`:
a record that cannot be consistent is a programming error, so the operation fails closed. The
store's `CHECK` constraints refuse it again. The scope, actor, chain, origin, and sponsor can
each be recovered from the row alone.
