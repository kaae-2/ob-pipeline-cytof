# GateMeClass frozen coverage policy

This directory freezes the GateMeClass investigative evidence at 2026-08-01
18:57 UTC. `cases.tsv` has one row for each of the 120 planned combinations of
four datasets, five folds, three filtering strata, and two GMM
parameterizations. It was transcribed from the controlled `state.json`; no
absolute workspace paths are retained.

The runtime findings and failure classifications are summarized in
[`POSTMORTEM.md`](POSTMORTEM.md).

| Dataset | Passed | Timed out | Interrupted | Pending |
|---|---:|---:|---:|---:|
| FR-FCM-Z238 | 30 | 0 | 0 | 0 |
| FR-FCM-Z3YR | 6 | 3 | 0 | 21 |
| FR-FCM-Z2KP-covid | 6 | 0 | 2 | 22 |
| FlowCyt | 1 | 0 | 0 | 29 |
| **Total** | **43** | **3** | **2** | **72** |

Only `passed` rows are eligible for supplementary reporting. Each has an
independent `PASS` validation record and the SHA-256 of its genuine prediction
archive. Timed-out, interrupted, and pending rows have no prediction hash and
must remain explicit missing coverage; they must never be represented by a
synthetic prediction or a metric value.
`output_archive_sha256=NA` is the explicit missing-value sentinel for those
rows, not an archive identifier.

The `runner_commit` column records actual provenance. Thirty FR-FCM-Z238 passes
and two FR-FCM-Z3YR passes used `68f94fb5f57d2ce27a0d70f8912ff2e48994f925`;
the other eleven passes and all terminal adverse records used
`da3fcb906345c5bd5dff879c34c548d25a3df9f8`. The latter commit changed only
prediction-label mapping: it keeps explicit `Unclassified` results as rejection
label `0` and fails on any other unmapped label instead of coercing it to zero.
The earlier outputs remain supplementary evidence because their archives were
independently checked for member names, row alignment, integer/domain validity,
and genuine model rejection labels. They are not misreported as outputs of the
later commit.

Four Z3YR rows with `status=pending` and return code `-15` were started and then
reset to pending when the original expansion orchestration was interrupted.
The two Z2KP rows classified as `interrupted` are the distinct persisted
failed-state records from the later safe supervisor. Neither class is a model
prediction or a timeout.

`Clustering_conda-reviewer-response.yml` remains the pinned investigative source
configuration. Omnibenchmark 0.3.2 cannot condition an analysis module on a
dataset parameter or declare its output optional, so
`Clustering_conda-reviewer-final.yml` omits GateMeClass entirely. The final
one-shot DAG runs the other six models over every configured dataset, fold, and
stratum. Final reporting may merge only the 43 frozen validated GateMeClass
cases, must provenance-check their archive hashes, and must display all four
coverage states alongside results.
