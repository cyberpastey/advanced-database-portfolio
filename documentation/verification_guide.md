# Technical verification preparation
Explain each answer using actual files and outputs, not memorised claims.

1. Why NUMERIC rather than float? Exact kobo, explicit two-decimal validation; no FX in this lab.
2. Why two entries? Their sum must be zero; funding is a clearing-to-customer transfer.
3. How is overspending prevented? Lock wallet rows in deterministic order before reading current ledger balance; execute all changes atomically. Raw DML is denied to the app role.
4. Does a lock protect all isolation levels identically? No: snapshot behaviour differs; REPEATABLE READ/SERIALIZABLE can abort and require a full retry.
5. What does a rollback do? Removes both entries, the transfer and its outbox event; sequences may still have gaps.
6. What is a reversal? An equal opposite new transfer with a unique original reference; history is retained and funds must be available.
7. What does an index improve? Selective retrieval or sorting; it costs writes/storage and may not help broad scans. Read actual rows, buffers and timings in the plan.
8. Why MongoDB? Variable risk metadata, not balances; document validation and unique IDs do not create cross-store referential integrity.
9. Is the outbox bridge implemented? No. Explain required retry/deduplication/lag handling before claiming delivery.
10. Is logical replication HA? No. The probe demonstrates async propagation/pause/catch-up, not automatic promotion, DDL replication or backup recovery.
11. What is truly individual? Describe your own edits, reruns, analysis and reflection; acknowledge AI support.
