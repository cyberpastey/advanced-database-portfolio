# Technical reflection
The PayFlow design separates transaction intent from the signed ledger entries that determine wallet balances. Deriving balances removes a mutable balance cache, but makes balance reads depend on aggregation and indexing. Deferred constraints check posting shape at commit; ordered wallet locks and application permissions address the concurrency problem that normalisation alone cannot solve.

The bulk-load failure was instructive at the implementation level: one transaction acquired 60,000 request-key advisory locks and exhausted PostgreSQL shared lock memory. Batches of 500 shortened lock lifetimes without weakening transfer-level atomicity. Two subsequent parameterisation errors were corrected before accepting the load. These were tool-observed development events, not a claim of personal student execution.

Both selected indexes reduced median execution time in this dataset, and the plans changed from sequential scans to bitmap access. The time-range plan still sorted its results; the index did not remove every operation. Warm-cache measurements and a fixed baseline-first order limit the strength of the performance conclusion. Production throughput and write amplification were not measured.

The concurrency test committed one competing withdrawal and rejected the other with insufficient funds, preserving a nonnegative balance. READ COMMITTED saw a later committed change; REPEATABLE READ retained its earlier snapshot; SERIALIZABLE rejected a conflicting update with 40001. These observations support explicit locking and complete-transaction retries rather than assuming a single isolation setting solves every race.

MongoDB was suitable for variable event metadata, while the PostgreSQL ledger remained authoritative. The local replication experiment showed both propagation and a deliberately stale subscriber during a pause. It did not establish automatic failover, cloud resilience or backup recoverability. Further work should test delivery retries, authenticated/TLS deployment, backup restoration and operational recovery targets.

Review status: the student confirmed review of the work on 5 November 2026. The discussion above describes verified project decisions and observations.
