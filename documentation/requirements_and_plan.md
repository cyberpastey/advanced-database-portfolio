# Requirements, compliance matrix and development plan
Source: official eight-page MIT 8103 assessment, read in full; two LMS screenshots. The official document governs conflicts. PostgreSQL/MongoDB, detailed scenarios and local replication are the student's selected implementation choices, not compulsory product choices in the assessment. Official Portfolio 5 permits discussion **or** setup. User requests practical execution wherever available.

| ID/source | Requirement | Deliverable | Evidence / acceptance |
|---|---|---|---|
| O1 pp1-2 | One realistic organisation, name, purpose, users, data, operations | README, P1 README | Consistent PayFlow names across all activities |
| O2 p3 (7 marks) | ERD, relational schema, keys, constraints, normalisation | P1 schema.sql, er_diagram.mmd, relational_schema.md, normalisation.md | DDL executes; negative constraint tests; diagram matches keys |
| O3 p3 (7) | Queries, results, plans, indexing, brief performance analysis | P2 queries.sql, indexes.sql, evidence | Genuine plans, result parity, repeated before/after observations |
| O4 p3 (7) | Commit, rollback, isolation, concurrency issue/control | P3 transfer function, scripts and runner | Two independent connections, assertions and raw logs |
| O5 p3 (7) | Same-case NoSQL model, implementation, suitability | P4 validator, JSON examples, runner | CRUD, invalid insert rejected, aggregation and index outputs |
| O6 p3 (6) | Distributed/cloud discussion or setup; replication/sharding/availability/consistency | P5 architecture, README, replication runner | Local logical-replication outputs if executable; no claimed cloud deployment |
| O7 pp3-4 (6) | 2-3-page LMS summary; all five activities, organisation, GitHub link, evidence, reflection, references/declaration | Final summary after verified results | Rendered 2-3 pages, functioning private link, authentic reflection |
| O8 p4 | Private GitHub, SQL, models, NoSQL, plans, performance, screenshots/config/tests, READMEs | Repository | Check private flag, tracked files and accepted assessor read access |
| O9 pp4-5 | Progressive commits throughout semester | Actual commit history | Only current work may be committed now; historical requirement cannot be recreated |
| O10 p5 | Individual work, understand/verify/explain, possible sampled verification | verification_guide.md; student review | Student reproduces tests and explains outputs |
| O11 pp5,7 | Individual reflection: choices, real challenges, lessons | technical_reflection.md | Student-written conclusions grounded in actual activity |
| O12 p7 | Acknowledge external sources/code/data/libraries; AI tool, use, student checks | references.md; ai_use_declaration.md | Accurate statement of what student actually reviewed |
| O13 p7 | All five complete, organised, evidence, README, correct LMS files, working accessible link | validation_report.md | No unverified item labelled complete |
| O14 p6 | Rubric: correctness 8, design 6, implementation 8, query analysis 5, advanced concepts 5, documentation/GitHub 5, reflection/understanding 3 | rubric_review.md | Traceable actual evidence, no guaranteed grade |
| L1 screenshots | Download question; keep original unchanged; use response form | Original untouched; separate outputs | No editing or submission of question PDF |
| L2 screenshots | <=20% similarity excluding bibliography | Original case-specific prose and citations | Institution determines score |
| L3 screenshots | One attempt, review; late policy | Submission checklist | Student authorises actual final submission |
| L4 screenshots | Surname_Firstname_StudentID folder; matching file prefix and descriptive type; no spaces/generic names; correct format | Odekunle_Ayoola_301904401 submission folder | Audit final upload filenames and form formats |
| U1 user | No fabricated results/screenshots/commits/reflection; fictional data only | All evidence and declarations | Execution status explicit |
| U2 user | Finance integrity, rollback, success, concurrency, isolation, recovery | Ledger and automated tests | Zero net ledger, no negative customer balance, exactly two entries per transfer |

## Architecture and decisions
Use PostgreSQL 17 with NUMERIC(18,2) NGN amounts, customers, wallets, immutable transfers, immutable ledger entries and an event outbox. Each posted movement has exactly one debit and one credit. A system clearing wallet is allowed to be negative to represent synthetic funding; customer wallets must not be. Opening customer funds are ledger transfers from clearing. Deposit/withdrawal are clearing-to-customer/customer-to-clearing movements in this simulation, without bank integration. Reversal is a new compensating transfer referencing an original once; it never edits historical money. No fee/FX/multi-currency settlement is modelled.

Row locks are acquired in wallet ID order. The database transfer function owns writes; application roles have SELECT and EXECUTE, not raw ledger DML. Deferred triggers validate balance, amounts and entry shape at commit. Privileged administrators can bypass safeguards; this lab does not claim tamper-proof administration. The outbox is committed with the ledger, but Mongo delivery, retries and a production fraud engine remain proposed.

MongoDB documents hold flexible risk-event metadata, indexed by event ID, wallet and time. PostgreSQL remains authoritative. A local logical subscriber demonstrates asynchronous data propagation and lag; it is not a hot standby and does not automatically replicate DDL, sequences or grant failover safety. Proposed cloud architecture adds separate availability zones, TLS, least privilege, backups/PITR, monitoring and tested fencing. Shard by wallet only after proving scale; cross-wallet atomic transfers become harder across shards. Partition old events by time first.

## Ordered execution and gates
1. Requirements and setup: confirm identity, inspect runtimes, create private repository when capability permits. Commit the actual plan.
2. P1: implement schema, generated data, constraint checks and reconciliation. Gate: all invariants pass. Record corrections.
3. P2: load sufficient deterministic data, collect raw results and EXPLAIN ANALYZE JSON for two queries, collect repeated tests after warming, verify equivalent outputs, report actual timings/buffers and limitations. Gate: no invented speedup.
4. P3: successful commit, forced rollback after posting, competing withdrawals, ordered-lock transfer, READ COMMITTED versus REPEATABLE READ and SERIALIZABLE conflict. Gate: terminal states, SQLSTATE and invariants verified.
5. P4: create validator/collection, insert synthetic events, CRUD/filter/aggregate/index/invalid-document tests. Gate: expected operations verified.
6. P5: configure publication/subscription, wait for actual replay and compare data; test interruption/recovery if available. Gate: identify consistency/availability limits.
7. Documentation: derive analysis from logs; student completes reflection and declaration; generate and visually check 2-3-page summary with working repository link.
8. Audit rubric, names, secrets, repository visibility/access and file format. Final review by student; never submit to LMS without explicit authorisation.

## Essential inputs still required
Identity is confirmed: Odekunle Ayoola, 301904401, GitHub cyberpastey. Assessor's GitHub username is not in the supplied PDF/screenshots and must be obtained from the lecturer. Student must independently reproduce/explain the work and supply their reflection. A functioning Docker Linux engine, image downloads and local database connections are needed for runtime evidence. GitHub repository creation/access may require a browser or authenticated CLI. Confirm accepted LMS file extension in the actual form. No cloud credential is required for the local alternative.
