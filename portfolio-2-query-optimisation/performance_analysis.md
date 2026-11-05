# Actual query and performance analysis
Dataset: 2,000 customers, 2,001 wallets, 62,001 transfers at benchmark time (2,000 funding, one application-role test and 60,000 benchmark transfers). Every movement has two balancing entries. Both queries have identical SQL before/after; the intervention is indexing, not a semantic rewrite. Full result equality is asserted.

| Query/business purpose | Rows | Before median ms | After median ms | First measured plan shared hits |
|---|---:|---:|---:|---|
| Ten-minute transaction audit | 600 | 15.223 | 0.461 | 1,387 to 14 |
| High-value review (>= NGN 100,000) | 2,000 | 20.129 | 1.590 | 1,387 to 31 |

The baseline plans use sequential scans followed by quicksort. They remove 61,401 and 60,001 rows respectively by filtering. After adding transfers_created_id and transfers_amount, both measured plans use Bitmap Index Scan and Bitmap Heap Scan, followed by Sort. More selective access substantially reduces buffer visits in these observations. The INCLUDE amount on the time index makes a covering path possible, but the observed plan is **not** index-only; do not claim that heap access or sorting was eliminated. No scan type was forced.

Five measured trials follow an excluded warm-up per condition. Medians above are server Execution Time, not application end-to-end latency. Buffers above are the first recorded measured plans, not medians. Raw JSON includes every trial's actual/estimated rows, timing, loops, buffers and node structure. All sampled plans had warm shared buffers, so these results are not disk I/O benchmarks.

Limitations: one host, synthetic distribution, baseline condition before indexed condition, cache/background-load effects and refreshed ANALYZE statistics. No concurrent production load, index maintenance cost or randomised crossover experiment was measured. Indexes require write work and storage; broad scans can still favour sequential access. The results demonstrate these two cases, not a universal speedup.
