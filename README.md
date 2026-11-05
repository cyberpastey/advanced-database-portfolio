# PayFlow: MIT 8103 Advanced Database Systems
Student: Odekunle Ayoola | 301904401 | Miva University, 2026/2027, First Semester.

PayFlow is a fictional Nigerian digital wallet platform. Customers register and view wallets and transfers; operations staff reconcile the ledger; fraud analysts investigate events; administrators manage availability. Only deterministic synthetic data is used. No payment service is connected.

## Reproduce
Install Docker Desktop with Linux containers and Python 3.11+. Create the ignored .env as described in SETUP.md. Start Docker, then run `docker compose up -d --wait` from this directory. Install `pip install -r requirements.txt` and run `python scripts/verify.py`. The runner rebuilds the payflow schema, replaces the project MongoDB events collection and recreates the replication probe in this project's containers; it is a repeatable laboratory, not a production migration. Run `docker compose down` to stop, retaining volumes. Do not run the reset against another database.

Default lab connections: PostgreSQL localhost:55432, database/user payflow; MongoDB localhost:57017. Both bind to loopback. Credentials are supplied in an ignored .env file; see SETUP.md. Raw evidence is saved per activity. A failed run is not evidence of a passing implementation. See documentation/validation_report.md for actual status.

## Architecture
PostgreSQL is authoritative for money. An immutable double-entry ledger records every transfer. Wallet rows are locked in ascending ID order before validating available funds. Balances are derived from ledger entries rather than kept in a second mutable cache. MongoDB stores supplementary synthetic fraud events. The proposed outbox consumer is an architectural extension, not an implemented cross-database delivery system. PostgreSQL logical replication is the planned local distributed exercise; automatic failover is not provided.

## Academic ownership
AI-assisted implementation and documentation require the student's independent review, execution and explanation. Read documentation/ai_use_declaration.md and complete the reflection after doing the exercises. No LMS submission has been made. Same-day commits cannot establish semester-long development.
