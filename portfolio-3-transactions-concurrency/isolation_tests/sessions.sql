-- Session A: repeat twice, substituting READ COMMITTED / REPEATABLE READ.
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT balance FROM payflow.wallet_balances WHERE wallet_id=2;
-- Pause and run session B, then repeat SELECT above and COMMIT.
-- Session B:
BEGIN;
SELECT payflow.post_transfer('isolation-manual-unique-key',3,2,1);
COMMIT;
-- READ COMMITTED gets a new statement snapshot. REPEATABLE READ retains snapshot.
-- The automated runner uses fresh keys and explicit synchronisation, no manual timing.
