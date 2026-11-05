SET search_path=payflow,public;
CREATE INDEX transfers_created_id ON transfers(created_at,transfer_id) INCLUDE(amount);
CREATE INDEX transfers_amount ON transfers(amount);
ANALYZE transfers;
