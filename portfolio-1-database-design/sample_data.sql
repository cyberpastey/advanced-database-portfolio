SET search_path=payflow,public;
INSERT INTO customers(full_name,email)
 SELECT 'Synthetic Customer '||i,'customer'||i||'@example.test' FROM generate_series(1,2000) i;
INSERT INTO wallets(kind) VALUES('clearing');
INSERT INTO wallets(customer_id,kind) SELECT customer_id,'customer' FROM customers ORDER BY customer_id;
-- All opening balances have real balancing clearing entries.
SELECT post_transfer('opening-'||wallet_id,1,wallet_id,100000) FROM wallets WHERE kind='customer';
