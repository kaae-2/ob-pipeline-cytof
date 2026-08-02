# Benchmark Repository

## What this repository is about

This repository defines the Omnibenchmark CyTOF workflow and execution config.
It contains:

- the benchmark topology (`Clustering_conda.yml`),
- pinned module repositories/commits,
- environment specs in `envs/`, and
- convenience commands in `justfile`.

The pipeline orchestrates data import, preprocessing, model analysis, metrics,
and metrics collection.

## How it works in Omnibenchmark

`ob run benchmark -b Clustering_conda.yml` executes the full DAG.

Data flow:

1. `data` -> `{name}.data.tar.gz`, `{name}.metadata.json.gz`, attachments
2. `preprocessing` -> train/test matrix + label tarballs + `label_key`
3. `analysis` -> `{model}_predicted_labels.tar.gz`
4. `metrics` -> `{name}.flow_metrics.json.gz`
5. `metric_collectors` -> HTML report + TSV summaries + plot archive

## Setup Guide

Use the bootstrap helper for a first local setup:

```bash
just bootstrap
```

The bootstrap script checks for `conda`, asks before downloading Miniforge if conda is missing, creates an `omnibenchmark` conda environment if needed, installs Omnibenchmark and helper dependencies, validates `Clustering_conda.yml`, and runs a local dry-run.

If you want to install without dry-running yet:

```bash
just bootstrap-no-dry-run
```

For non-interactive setup on a machine where installing Miniforge and creating the env is acceptable:

```bash
python scripts/bootstrap_omnibenchmark.py --yes
```

The script uses:

```text
Conda prefix: ~/miniforge3
Conda env: omnibenchmark
TMPDIR: ~/tmp
CONDA_PKGS_DIRS: ~/conda-pkgs
```

Override these with:

```bash
python scripts/bootstrap_omnibenchmark.py \
  --conda-prefix ~/miniforge3 \
  --env-name omnibenchmark \
  --tmpdir ~/tmp \
  --conda-pkgs-dir ~/conda-pkgs
```

### Manual Setup

Example conda setup for running Omnibenchmark CLI locally:

```bash
conda create -n omnibenchmark python=3.11 -y
conda activate omnibenchmark
python -m pip install --upgrade pip
python -m pip install omnibenchmark
```

Optional helper tools:

```bash
python -m pip install just
```

Verify CLI:

```bash
ob --help
```

Validate the benchmark config before running:

```bash
just validate-config
```

Dry-run the DAG before executing real jobs:

```bash
just dry-run
```

Useful Omnibenchmark docs:

- Docs home: <https://docs.omnibenchmark.org/latest/>
- CLI reference: <https://docs.omnibenchmark.org/latest/reference/>
- Tutorials: <https://docs.omnibenchmark.org/latest/tutorial/>
- Project site: <https://omnibenchmark.org>

## How to run

The final reviewer one-shot configuration intentionally omits GateMeClass. Run
it without `--continue-on-error`, which would permit placeholder outputs after
module failures:

```bash
TMPDIR="$HOME/tmp" CONDA_PKGS_DIRS="$HOME/conda-pkgs" \
CYGATE_JAVA_XMS=512m CYGATE_JAVA_XMX=6g \
KNN_N_JOBS="$(( $(nproc) - 2 ))" \
ob run benchmark -b Clustering_conda-reviewer-final.yml \
  --local-storage --cores "$(nproc)" \
  --default-resources mem_mb=12000 \
  --resources mem_mb=52000
```

`Clustering_conda-reviewer-response.yml` is the investigative source retaining
the pinned GateMeClass module. Its frozen partial evidence and reporting policy
are in [`coverage/gatemeclass/`](coverage/gatemeclass/); it is not the final
end-to-end invocation.

Validate every benchmark configuration and the GateMeClass coverage ledger:

```bash
python scripts/validate_benchmark_config.py --all
```

```bash
ob run benchmark -b Clustering_conda.yml --local-storage --dry-run
ob run benchmark -b Clustering_conda.yml --local-storage --cores 6
```

The `just` shortcuts are:

```bash
just dry-run
just run
just check-config
```

## Resource-controlled run command

For larger runs, use explicit limits in one command:

```bash
TMPDIR="$HOME/tmp" CONDA_PKGS_DIRS="$HOME/conda-pkgs" \
CYGATE_JAVA_XMS=512m CYGATE_JAVA_XMX=6g \
GATEMECLASS_CORES=1 GATEMECLASS_BLAS_THREADS=1 \
KNN_N_JOBS="$(( $(nproc) - 2 ))" \
ob run benchmark -b Clustering_conda.yml --local-storage --cores "$(nproc)" \
  --default-resources mem_mb=12000 \
  --resources mem_mb=52000 \
  --set-resources \
  analysis_knn_default:mem_mb=11000 \
  analysis_cygate_default:mem_mb=7500 \
  analysis_random_default:mem_mb=1000 \
  analysis_dgcytof_default:mem_mb=7000 \
  analysis_cyanno_default:mem_mb=6000 \
  analysis_lda_default:mem_mb=2500 \
  analysis_gatemeclass_.3c530339a11d8427b017a7815187a9925e6f400b3dc60e8c49021043cb0ad155:mem_mb=5500 \
  analysis_gatemeclass_.d51d2d4cdd7aa7a8932ed1b2ec95e100abe8ba09548fb2327f68b81dff72cd40:mem_mb=5500 \
  preprocessing_data_preprocessing_.34887b980ba1bc5c62edd21ce45ff723e243427e7d7c20d12ef05ee2521ca105:mem_mb=4500 \
  preprocessing_data_preprocessing_.3cd57f101f52cc8f1e65c10f45eaf594947077c8d9def5332ec922b6e338c80d:mem_mb=4500 \
  preprocessing_data_preprocessing_.847bfb0d4a973df0f35c11bf99fb6e1b94f2357ab40f07caaf9534b6ad686016:mem_mb=4500 \
  preprocessing_data_preprocessing_.9dd08836375b103e2223f5ed2ef89b109cd6fbc84f23cb9af6f288162657760c:mem_mb=4500 \
  preprocessing_data_preprocessing_.f4da8dc0c51bb7e3b609c1335cea939b4742db96f4b5b3c99873cbeca174a532:mem_mb=4500 \
  metrics_flow_metrics_default:mem_mb=2500
```

Parameters used:

- `just run` -> `--cores 6`
- `just dry-run` -> `--dry-run`
- Default per-job memory (`--default-resources`): `12000` MB
- Total memory pool (`--resources mem_mb`): `52000` MB
- Model-specific caps:
  - `analysis_knn_default` -> `11000` MB
  - `analysis_cygate_default` -> `7500` MB
  - `analysis_dgcytof_default` -> `7000` MB
  - `analysis_cyanno_default` -> `6000` MB
  - `analysis_gatemeclass_.3c530339...`, `analysis_gatemeclass_.d51d2d4c...` -> `5500` MB
  - `analysis_lda_default` -> `2500` MB
  - `analysis_random_default` -> `1000` MB
  - `metrics_flow_metrics_default` -> `2500` MB
  - `preprocessing_data_preprocessing_.*` (5 known parameter hashes) -> `4500` MB

## Extending or using the tool

1. Edit `Clustering_conda.yml` to add/change stages, params, or module pins.
2. Add/update software env specs under `envs/`.
3. Keep module CLI input ids aligned with YAML input ids.
4. Omnibenchmark uses specific commit hashes to pull modules which needs to be pinned in the YAML file. 
5. Validate with dry-run before full execution.

Guided helpers are available for the two common extension paths:

```bash
just add-dataset
just add-model
just validate-config
just check-config
```

`just add-dataset` supports two modes:

- Add an existing prepared dataset through the shared `data_import` module. The helper loads available dataset names from <https://github.com/kaae-2/ob-flow-datasets/tree/main/prepared> and asks you to select one.
- Add a new dataset module from another GitHub repository. The helper adds a new `stages.data.modules` entry and prints the required output contract for downstream preprocessing and metrics.

For external dataset modules, the helper checks the selected GitHub repository for a `config.cfg` file with an entry point. If it cannot find one, it warns and prints the expected module contract. A recommended minimal `config.cfg` is:

```ini
[module]
entry_point = python run_dataset.py
```

Every data module must emit these output ids:

```text
data.raw
data.import_metadata
```

The expected files are:

```text
${output_dir}/${name}.data.tar.gz
${output_dir}/${dataset}.${name}.metadata.json.gz
```

The metadata must include stable sample identifiers, feature/channel names, label metadata, optional batch metadata, and enough run metadata for downstream metrics and collector de-duplication.

`just add-model` asks for a GitHub repository first, resolves a pinned commit, inspects setup files, and can generate a starter conda environment for Python, R, or Bash models under `envs/`.

It also checks the model repository for `config.cfg` with an entry point. A recommended minimal model `config.cfg` is:

```ini
[module]
entry_point = python run_model.py
```

Every analysis module must accept:

```text
--name
--output_dir
--data.train_matrix
--data.train_labels
--data.test_matrix
--data.metadata
```

Every analysis module must write:

```text
${output_dir}/${name}_predicted_labels.tar.gz
```

### Helper Limitations

- The helpers edit `Clustering_conda.yml`; review `git diff` before committing.
- GitHub repository inspection requires network access and may be rate-limited without `GITHUB_TOKEN` or `GH_TOKEN`.
- Environment generation is best-effort. Python `requirements.txt`, R metadata, and Bash scripts are detected, but complex system dependencies still need manual edits in `envs/*.yml`.
- `config.cfg` entry point checks are warnings, not hard failures, because older modules may not have adopted the convention yet.
- `just validate-config` validates benchmark YAML structure and local env files; it does not execute model code.
- `just dry-run` checks DAG readiness; it does not prove a full benchmark run has enough memory, disk, or wall time.

### Code example: add a new analysis tool

Add a software environment under `software_environments` and a module under
`stages.analysis.modules`.

```yaml
software_environments:
  my_tool_env:
    description: My tool environment
    conda: envs/my_tool.yml
    envmodule: my_tool_env

stages:
  - id: analysis
    inputs:
      - entries:
          - data.train_matrix
          - data.train_labels
          - data.test_matrix
          - data.metadata
    modules:
      - id: my_tool
        name: My Tool
        software_environment: my_tool_env
        repository:
          url: https://github.com/<your-org>/ob-pipeline-my-tool.git
          commit: <pinned-commit-sha>
        parameters:
          - values: [--some-param, value]
    outputs:
      - id: analysis.prediction
        path: "{input}/{stage}/{module}/{params}/{dataset}_predicted_labels.tar.gz"
```

Tool implementation contract (analysis stage):

- Mandatory inputs:
  - `--name`
  - `--output_dir`
- Stage inputs (all current `stages.analysis.inputs.entries`):
  - `--data.train_matrix`
  - `--data.train_labels`
  - `--data.test_matrix`
  - `--data.metadata`
- Configurable inputs:
  - anything you add under `modules[].parameters[].values` (for example
    `--some-param value`)

Expected output:

- Filename your tool must write: `${output_dir}/${name}_predicted_labels.tar.gz`
- Benchmark output mapping (from `Clustering_conda.yml`):
  `analysis.prediction -> {input}/{stage}/{module}/{params}/{dataset}_predicted_labels.tar.gz`

Example invocation shape your tool should support:

```bash
python run_my_tool.py \
  --name my_tool \
  --output_dir out/data/analysis/default/my_tool \
  --data.train_matrix out/data/data_preprocessing/default/data_import.train.matrix.tar.gz \
  --data.train_labels out/data/data_preprocessing/default/data_import.train.labels.tar.gz \
  --data.test_matrix out/data/data_preprocessing/default/data_import.test.matrices.tar.gz \
  --data.metadata out/data/data_preprocessing/default/data_import.metadata.json.gz \
  --some-param value
```

## Adding datasets

1. Add dataset entries/params in the data stage of `Clustering_conda.yml`.
2. Ensure the `data` module can import that dataset.
3. Run dry-run, then run a bounded test execution.

Dataset source and loading references:

- Dataset repository: <https://github.com/kaae-2/ob-flow-datasets>
- Prepared datasets folder: <https://github.com/kaae-2/ob-flow-datasets/tree/main/prepared>
- Dataset import/packaging implementation: <https://github.com/kaae-2/ob-pipeline-data/blob/main/data_import.py>
- Import runner script: <https://github.com/kaae-2/ob-pipeline-data/blob/main/run_data_import.sh>

## Forking this toolchain

1. Fork the module repositories you want to maintain.
2. Update repository URLs/commits in `Clustering_conda.yml`.
3. Keep module CLIs compatible with current input ids (or update dependent ids
   consistently).
4. Re-run dry-run and one full end-to-end execution.
