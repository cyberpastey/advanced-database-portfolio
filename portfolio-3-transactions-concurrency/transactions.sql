SET search_path=payflow,public;
BEGIN;
SELECT post_transfer('manual-success',2,3,100);
COMMIT;
SELECT * FROM wallet_balances WHERE wallet_id IN(2,3);
BEGIN;
SELECT post_transfer('manual-rollback',2,3,25);
ROLLBACK;
SELECT count(*) AS must_be_zero FROM transfers WHERE request_key='manual-rollback';
