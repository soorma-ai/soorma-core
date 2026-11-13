-- SPDX-License-Identifier: FSL-1.1-ALv2
--
-- D-ET-07 in the store (U7 NFR Design NP-ET-14; BR-AT-ET-06): P7's envelope
-- rule closed both ways. 0004 says an envelope-free operation
-- (exchangeBootstrap, renewAgentCredential) carries no envelope; this says an
-- agent record for any other operation carries one, so its chain is present
-- (and, through U4's attribution_envelope_all_or_none, its origin and
-- re-broadening outcome). P7's writer refuses the same before any SQL. Alone in
-- its own migration, as 0004; 0001 to 0004 are not changed.
ALTER TABLE attribution_records
  ADD CONSTRAINT attribution_envelope_bearing_operations CHECK (
    actor_kind <> 'agent'
    OR operation IN ('exchangeBootstrap', 'renewAgentCredential')
    OR chain IS NOT NULL
  );
