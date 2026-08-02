# GateMeClass runtime post-mortem

Evidence was frozen at 2026-08-01 18:57 UTC. No result in this directory was
generated for the final policy change. The controlled investigation used one
GateMeClass worker, one BLAS thread, and a four-hour per-job timeout.

## Finding

The 120-case matrix ended with 43 independently validated prediction archives,
3 timeouts, 2 interrupted failed-state records, and 72 pending cases. This is a
partial supplementary result, not balanced coverage comparable to methods that
complete the final end-to-end DAG.

- FR-FCM-Z238 completed all 30 fold/stratum/GMM combinations.
- FR-FCM-Z3YR completed 6 cases; three GMM E cases reached four hours during
  test annotation, establishing a known feasibility boundary.
- FR-FCM-Z2KP-covid completed all 6 fold-1 cases. Its two fold-2 records ended
  together on supervisor SIGTERM and are interruptions, not model timeouts or
  invalid predictions.
- FlowCyt completed one fold-1 unfiltered GMM E case. Its remaining 29 cases do
  not have a supported feasibility conclusion.

Four additional Z3YR attempts were interrupted by the earlier orchestration and
reset to pending. Their partial elapsed times are not completion endpoints and
remain `pending` in the ledger.

## Output integrity

Every `passed` archive was independently checked for expected member names, row
alignment with test inputs, integer labels, and metadata-domain validity. The
ledger records each archive SHA-256 and actual runner commit. No non-passing row
has an archive hash; `NA` marks that missing field in the TSV.

Prediction label `0` is retained only when GateMeClass itself returned the
explicit `Unclassified` rejection outcome. Some validated GMM V members are
genuinely all zero for that reason. Exclusions, exceptions, timeouts,
interruptions, and pending cases never receive generated all-zero archives and
must never enter metrics as predictions.

## Runtime mechanism

Each job trains a marker table and annotates test members sequentially at the
controlled worker setting. The initial gating pass samples 10% of cells, but a
partly classified sample then invokes KNN refinement over unsampled and
unclassified cells, so work can return to nearly the full sample. An entirely
unclassified initial pass skips KNN, which explains why some high-rejection GMM
V cases were faster. Runtime therefore depends on marker count, member count,
sample size, fold-specific training data, and rejection behavior rather than
cell count alone.

## Publication policy

Final reporting may merge only the 43 hash-identified `passed` cases as a
clearly marked supplementary GateMeClass set. Reports must show passed,
timed-out, interrupted, and pending counts by dataset and case, and pair
performance with completion coverage and rejection rates. No missing case may
be imputed, scored, or represented as a prediction.
