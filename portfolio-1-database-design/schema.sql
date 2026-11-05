DROP SCHEMA IF EXISTS payflow CASCADE;
CREATE SCHEMA payflow;
SET search_path=payflow,public;
CREATE TABLE customers (
 customer_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 full_name text NOT NULL CHECK(length(full_name)>0),
 email text NOT NULL UNIQUE CHECK(email LIKE '%@example.test'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE wallets (
 wallet_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 customer_id bigint REFERENCES customers,
 kind text NOT NULL CHECK(kind IN ('customer','clearing')),
 currency text NOT NULL DEFAULT 'NGN' CHECK(currency='NGN'),
 UNIQUE(customer_id,currency),
 CHECK((kind='customer')=(customer_id IS NOT NULL))
);
CREATE UNIQUE INDEX single_clearing_wallet ON wallets(kind) WHERE kind='clearing';
CREATE TABLE transfers (
 transfer_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 request_key text NOT NULL UNIQUE,
 sender_id bigint NOT NULL REFERENCES wallets,
 receiver_id bigint NOT NULL REFERENCES wallets,
 amount numeric(18,2) NOT NULL CHECK(amount>0 AND amount<10000000000000000),
 status text NOT NULL DEFAULT 'posted' CHECK(status='posted'),
 reversal_of bigint UNIQUE REFERENCES transfers,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(sender_id<>receiver_id)
);
CREATE TABLE ledger_entries (
 entry_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 transfer_id bigint NOT NULL REFERENCES transfers,
 wallet_id bigint NOT NULL REFERENCES wallets,
 amount numeric(18,2) NOT NULL CHECK(amount<>0 AND abs(amount)<10000000000000000),
 UNIQUE(transfer_id,wallet_id)
);
CREATE INDEX ledger_wallet ON ledger_entries(wallet_id);
CREATE TABLE outbox_events (
 event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 transfer_id bigint NOT NULL UNIQUE REFERENCES transfers,
 event_type text NOT NULL DEFAULT 'transfer.posted',
 payload jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 delivered_at timestamptz
);
CREATE VIEW wallet_balances AS
 SELECT w.wallet_id,w.customer_id,w.kind,w.currency,coalesce(sum(l.amount),0) AS balance
 FROM wallets w LEFT JOIN ledger_entries l USING(wallet_id)
 GROUP BY w.wallet_id;

CREATE FUNCTION immutable_history() RETURNS trigger LANGUAGE plpgsql SET search_path=payflow,pg_temp AS $$
BEGIN RAISE EXCEPTION 'Financial history is append only' USING ERRCODE='23514'; END $$;
CREATE TRIGGER ledger_immutable BEFORE UPDATE OR DELETE ON ledger_entries
 FOR EACH ROW EXECUTE FUNCTION immutable_history();
CREATE TRIGGER transfers_immutable BEFORE UPDATE OR DELETE ON transfers
 FOR EACH ROW EXECUTE FUNCTION immutable_history();

CREATE FUNCTION validate_posting() RETURNS trigger LANGUAGE plpgsql SET search_path=payflow,pg_temp AS $$
DECLARE t transfers%ROWTYPE; n int; net numeric; debit numeric; credit numeric;
BEGIN
 IF TG_TABLE_NAME='transfers' THEN t:=NEW;
 ELSE SELECT * INTO t FROM transfers WHERE transfer_id=NEW.transfer_id; END IF;
 SELECT count(*),sum(amount),
 sum(amount) FILTER(WHERE wallet_id=t.sender_id),
 sum(amount) FILTER(WHERE wallet_id=t.receiver_id)
 INTO n,net,debit,credit FROM ledger_entries WHERE transfer_id=t.transfer_id;
 IF n<>2 OR net IS DISTINCT FROM 0::numeric
 OR debit IS DISTINCT FROM -t.amount OR credit IS DISTINCT FROM t.amount THEN
 RAISE EXCEPTION 'Unbalanced or malformed transfer %',t.transfer_id USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM wallet_balances WHERE wallet_id IN(t.sender_id,t.receiver_id)
 AND kind='customer' AND balance<0) THEN
 RAISE EXCEPTION 'Negative customer balance' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER transfer_balance AFTER INSERT ON transfers
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_posting();
CREATE CONSTRAINT TRIGGER entry_balance AFTER INSERT ON ledger_entries
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_posting();

CREATE FUNCTION post_transfer(p_key text,p_sender bigint,p_receiver bigint,p_amount numeric,
 p_reversal bigint DEFAULT NULL) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=payflow,pg_temp AS $$
DECLARE id bigint; old transfers%ROWTYPE; original transfers%ROWTYPE; available numeric;
BEGIN
 IF p_key IS NULL OR p_sender IS NULL OR p_receiver IS NULL OR p_amount IS NULL
 OR p_amount<=0 OR p_amount<>round(p_amount,2) OR p_amount>=10000000000000000
 OR p_sender=p_receiver THEN RAISE EXCEPTION 'Invalid transfer input' USING ERRCODE='22023'; END IF;
 -- Serialise duplicate request keys as well as competing wallet operations.
 PERFORM pg_advisory_xact_lock(hashtextextended(p_key,0));
 SELECT * INTO old FROM transfers WHERE request_key=p_key;
 IF FOUND THEN
 IF (old.sender_id,old.receiver_id,old.amount,old.reversal_of)
 IS DISTINCT FROM (p_sender,p_receiver,p_amount,p_reversal) THEN
 RAISE EXCEPTION 'Idempotency key reused with different arguments' USING ERRCODE='22023'; END IF;
 RETURN old.transfer_id; END IF;
 PERFORM wallet_id FROM wallets WHERE wallet_id IN(p_sender,p_receiver) ORDER BY wallet_id FOR UPDATE;
 IF (SELECT count(*) FROM wallets WHERE wallet_id IN(p_sender,p_receiver))<>2 THEN
 RAISE EXCEPTION 'Unknown wallet' USING ERRCODE='23503'; END IF;
 IF p_reversal IS NOT NULL THEN
 SELECT * INTO original FROM transfers WHERE transfer_id=p_reversal;
 IF NOT FOUND OR original.reversal_of IS NOT NULL
 OR (original.sender_id,original.receiver_id,original.amount)
 IS DISTINCT FROM (p_receiver,p_sender,p_amount) THEN
 RAISE EXCEPTION 'Reversal must exactly compensate an original transfer' USING ERRCODE='22023'; END IF;
 END IF;
 SELECT balance INTO available FROM wallet_balances WHERE wallet_id=p_sender AND kind='customer';
 IF available IS NOT NULL AND available<p_amount THEN
 RAISE EXCEPTION 'Insufficient funds' USING ERRCODE='23514'; END IF;
 INSERT INTO transfers(request_key,sender_id,receiver_id,amount,reversal_of)
 VALUES(p_key,p_sender,p_receiver,p_amount,p_reversal) RETURNING transfer_id INTO id;
 INSERT INTO ledger_entries(transfer_id,wallet_id,amount)
 VALUES(id,p_sender,-p_amount),(id,p_receiver,p_amount);
 INSERT INTO outbox_events(transfer_id,payload)
 VALUES(id,jsonb_build_object('transfer_id',id,'sender_id',p_sender,'receiver_id',p_receiver,'amount',p_amount));
 RETURN id;
END $$;
REVOKE ALL ON FUNCTION post_transfer(text,bigint,bigint,numeric,bigint) FROM PUBLIC;
-- Group role has no login; actual login provisioning belongs outside version control.
DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='payflow_app') THEN
 CREATE ROLE payflow_app NOLOGIN; END IF; END $$;
GRANT USAGE ON SCHEMA payflow TO payflow_app;
GRANT SELECT ON ALL TABLES IN SCHEMA payflow TO payflow_app;
GRANT EXECUTE ON FUNCTION post_transfer(text,bigint,bigint,numeric,bigint) TO payflow_app;

