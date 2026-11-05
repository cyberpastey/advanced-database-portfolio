SET search_path=payflow,public;
-- Q1 History, multiple joins, ordered/filterable. Benchmark wallet 2.
SELECT t.transfer_id,t.created_at,t.amount,l.amount AS signed_amount,c.full_name
FROM ledger_entries l JOIN transfers t USING(transfer_id)
JOIN wallets w USING(wallet_id) LEFT JOIN customers c USING(customer_id)
WHERE l.wallet_id=2 ORDER BY t.created_at DESC,t.transfer_id DESC LIMIT 20;
-- Q2 Monthly volume, conditional aggregate and HAVING.
SELECT date_trunc('month',created_at) AS month,count(*) AS volume,sum(amount) AS value
FROM transfers GROUP BY 1 HAVING count(*)>10 ORDER BY 1;
-- Q3 Above-average movements (scalar subquery).
SELECT transfer_id,amount FROM transfers WHERE amount>(SELECT avg(amount) FROM transfers)
ORDER BY amount DESC LIMIT 20;
-- Q4 CTE and window running balance.
WITH activity AS (
 SELECT l.wallet_id,t.transfer_id,t.created_at,l.amount FROM ledger_entries l
 JOIN transfers t USING(transfer_id) WHERE l.wallet_id=2)
SELECT *,sum(amount) OVER(PARTITION BY wallet_id ORDER BY created_at,transfer_id
 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_balance
FROM activity ORDER BY created_at,transfer_id;
-- Q5 Reversed movements; original remains immutable.
SELECT o.transfer_id AS original,r.transfer_id AS reversal,o.amount
FROM transfers o JOIN transfers r ON r.reversal_of=o.transfer_id;
-- Q6 Customer balances and customer activity.
SELECT c.customer_id,c.full_name,b.balance,count(l.entry_id) AS entry_count
FROM customers c JOIN wallet_balances b USING(customer_id)
LEFT JOIN ledger_entries l USING(wallet_id)
GROUP BY c.customer_id,b.balance ORDER BY c.customer_id LIMIT 20;
-- Q7 Outbox audit, not failed request audit.
SELECT event_id,transfer_id,event_type,created_at,delivered_at FROM outbox_events
WHERE delivered_at IS NULL ORDER BY event_id LIMIT 20;
-- Q8 Selective high-value/time query used for index benchmark.
SELECT transfer_id,created_at,amount FROM transfers
WHERE created_at>='2026-01-20' AND created_at<'2026-01-21' AND amount>=50
ORDER BY created_at,transfer_id;
