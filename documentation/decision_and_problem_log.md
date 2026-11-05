# Actual decisions, problems and corrections
5 November 2026. All entries below describe tool-assisted development, not claimed student experience.

1. Chose ledger-derived balances to avoid a second mutable balance cache. Row locks are on wallet rows; restricted application writes and commit-time validation complement those locks.
2. Initial Docker inspection failed because its engine was stopped. Started Docker Desktop and verified its Linux engine; the restricted tool environment required access escalation to connect to its named pipe.
3. The default Windows Python alias could not run. Used the bundled Python runtime. Network restrictions prevented initial driver installation; downloaded drivers into workspace work/python_deps with approved network access.
4. Restricted GitHub CLI checks reported an invalid credential, but a check in the authorised host environment succeeded. Created cyberpastey/advanced-database-portfolio as private and pushed genuine current commits. Never printed credentials.
5. Added a fixed schema search_path to deferred trigger functions before testing so commit-time validation does not depend on the caller's search_path.
6. First P2 run failed with PostgreSQL `out of shared memory`, suggesting max_locks_per_transaction. The loader had acquired a unique advisory transaction lock for every one of 60,000 idempotency keys. Changed to batches of 500, reducing lock lifetime and deferred-trigger queues rather than inflating server limits.
7. The parameterised batch query exposed literal `%` handling in Psycopg, then ambiguous smallint overload resolution for generate_series. Escaped modulo as `%%` and explicitly cast series bounds to integer. These are actual observed failures; they were not passing tests.
8. Performance evidence uses five warmed measurements per condition, baseline then indexed, with equality checks. It does not alternate conditions; condition order and cache effects are disclosed limitations.

Student actions, explanations and lessons must be added only after the student performs them.
