-- Two terminals. Session A (run first):
BEGIN;
SELECT payflow.post_transfer('manual-lock-A',2,3,10);
SELECT pg_sleep(10);
COMMIT;
-- Session B while A sleeps: blocks on shared wallet, then validates newest balance.
BEGIN;
SET LOCAL lock_timeout='15s';
SELECT payflow.post_transfer('manual-lock-B',2,4,10);
COMMIT;
-- Inspect lock waits from third terminal if desired:
SELECT pid,wait_event_type,wait_event FROM pg_stat_activity WHERE datname='payflow';
