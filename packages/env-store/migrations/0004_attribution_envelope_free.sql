-- SPDX-License-Identifier: FSL-1.1-ALv2
--
-- D-AC-33 in the store (U6 NFR Design NP-AC-02; BR-AT-AC-02): exchangeBootstrap
-- and renewAgentCredential never carry an envelope (GAP-INT-008), so their
-- attribution records carry no chain and, through U4's
-- attribution_envelope_all_or_none, no origin or re-broadening outcome. The
-- operation itself states why. P7's writer refuses the same before any SQL.
-- Alone in its own migration, so the amendment to U4's table is reviewed on its
-- own; 0001 and 0002 are not changed. The reverse rule (an agent record for any
-- other operation must carry envelope facts) is U7's.
ALTER TABLE attribution_records
  ADD CONSTRAINT attribution_envelope_free_operations CHECK (
    operation NOT IN ('exchangeBootstrap', 'renewAgentCredential')
    OR (actor_kind = 'agent' AND chain IS NULL)
  );
