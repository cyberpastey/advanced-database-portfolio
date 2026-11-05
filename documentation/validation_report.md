# Final validation report - review stage, 5 November 2026
Status vocabulary: **Completed and verified**, **Implemented but not yet verified**, **Not implemented**, **Blocked by unavailable access/information**. Tool execution does not establish independent student understanding.

| Requirement | Status | Evidence / remaining action |
|---|---|---|
| Eight-page PDF and both screenshots read | Completed and verified | requirements_and_plan.md; source unchanged |
| Case study, stakeholders, operations, keys, 3NF | Completed and verified | P1 model/DDL/normalisation, matching execution |
| Schema, synthetic load, constraints | Completed and verified | P1 evidence/verification.json; 9 rejection tests, app function test |
| Financial reconciliation | Completed and verified | Zero total ledger, zero negative customers, zero malformed transfers/missing outbox |
| Query execution and two optimisations | Completed and verified | P2 raw plans, eight result sets, five trials per condition, equality checks |
| Commit, rollback, reversal, key retry | Completed and verified | P3 evidence/scenarios.json |
| Concurrent withdrawal, real lock wait, isolation | Completed and verified | P3 scenarios; observed Lock/transactionid and 40001 conflict |
| Normal restart durability | Completed and verified | P3 durability.json; committed transfer and invariants survived |
| MongoDB model, CRUD, aggregation, indexes, validation | Completed and verified | P4 operations.json; 100 inserted, one updated/deleted, 99 remain |
| Local logical replication and pause/catch-up | Completed and verified | P5 replication.json; two nodes, marker equality |
| Cloud deployment, HA failover, backup restore | Not implemented | Explicitly proposed only; official P5 permits discussion/setup alternative |
| Production PostgreSQL-to-Mongo event consumer | Not implemented | Outbox exists; delivery bridge described as future work |
| READMEs and reproduction runner | Completed and verified | Runner executed all five phases successfully; drivers recorded |
| Diagrams | Completed and verified | Mermaid source and SVG exports matched to schema/topology |
| Sources and AI assistance recorded | Completed and verified | references.md and AI declaration accurately disclose tool work |
| Independent student review/understanding | Implemented but not yet verified | Verification guide supplied; student must demonstrate actual review/reruns |
| Individual reflection | Implemented but not yet verified | Evidence-based draft; student review/personal contribution pending |
| Three-page summary review PDF | Completed and verified | Page count and rendered layout checked; remains a review draft |
| Private GitHub repository | Completed and verified | cyberpastey/advanced-database-portfolio; private flag checked |
| Current progressive commits | Completed and verified | Actual current development commits only |
| Evidence of semester-long activity | Not implemented | Cannot be manufactured retrospectively; discuss honest available history with lecturer if needed |
| Assessor access | Blocked by unavailable access/information | Assessor username not in attachments; obtain username, invite read access, confirm acceptance |
| Upload filenames and outer folder | Completed and verified | Prefix Odekunle_Ayoola_301904401; no spaces; zip keeps normal internal source names |
| Accepted LMS extension | Blocked by unavailable access/information | Check actual response form; supplied sources do not specify |
| Similarity screening | Not implemented | Institution runs screening; <=20% excluding bibliography required, not guaranteed |
| Final LMS submission | Not implemented | Requires student review and explicit submission authorisation; one attempt |

No automatic approval rejection occurred. Local execution needed approved host access for Docker/network/GitHub. No secrets are included in the upload zip; .env remains local and ignored. Raw output logs are genuine evidence; no screenshots were fabricated. The supplied instructions accept outputs/logs where applicable. A database-GUI screenshot collection has not been created.
