#!/usr/bin/env python3
"""Validate the benchmark YAML shape used by the helper scripts."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path
from typing import Any

from benchmark_config import find_stage, load_config


SHA_RE = re.compile(r'^[0-9a-fA-F]{7,40}$')
FINAL_CONFIG = 'Clustering_conda-reviewer-final.yml'
INVESTIGATIVE_CONFIG = 'Clustering_conda-reviewer-response.yml'
FINAL_MODELS = {'cygate', 'cyanno', 'dgcytof', 'knn', 'lda', 'random'}
GATEMECLASS_COMMIT = 'da3fcb906345c5bd5dff879c34c548d25a3df9f8'
DGCYTOF_COMMIT = '94edd10af5037ab20ceb2a2024beefa09d3313b9'
METRICS_COMMIT = '795246cf09ed95d4c3df916273f7cfc60b7f45b1'
FINAL_METRICS = ('accuracy', 'precision', 'recall', 'balanced_accuracy', 'f1')
EXPECTED_COVERAGE_COUNTS = Counter(
    {'passed': 43, 'timed_out': 3, 'interrupted': 2, 'pending': 72}
)
EXPECTED_DATASET_STATUS_COUNTS = Counter(
    {
        ('FR-FCM-Z238', 'passed'): 30,
        ('FR-FCM-Z3YR', 'passed'): 6,
        ('FR-FCM-Z3YR', 'timed_out'): 3,
        ('FR-FCM-Z3YR', 'pending'): 21,
        ('FR-FCM-Z2KP-covid', 'passed'): 6,
        ('FR-FCM-Z2KP-covid', 'interrupted'): 2,
        ('FR-FCM-Z2KP-covid', 'pending'): 22,
        ('FlowCyt', 'passed'): 1,
        ('FlowCyt', 'pending'): 29,
    }
)
LEGACY_GATEMECLASS_COMMIT = '68f94fb5f57d2ce27a0d70f8912ff2e48994f925'
EXPECTED_PASSED_RUNNER_COUNTS = Counter(
    {LEGACY_GATEMECLASS_COMMIT: 32, GATEMECLASS_COMMIT: 11}
)


def error(errors: list[str], message: str) -> None:
    errors.append(message)


def output_ids(module_or_stage: dict[str, Any]) -> set[str]:
    return {
        output.get('id')
        for output in module_or_stage.get('outputs', [])
        if output.get('id')
    }


def modules_by_id(stage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        module['id']: module
        for module in stage.get('modules', [])
        if isinstance(module, dict) and module.get('id')
    }


def final_metrics_parameters() -> list[dict[str, list[str]]]:
    return [{'values': ['--metric', ','.join(FINAL_METRICS)]}]


def validate_final_metrics(metrics_stage: dict[str, Any], errors: list[str]) -> None:
    flow_metrics = modules_by_id(metrics_stage).get('flow_metrics')
    if not flow_metrics:
        error(errors, 'final reviewer config must contain flow_metrics')
        return

    if flow_metrics.get('repository', {}).get('commit') != METRICS_COMMIT:
        error(errors, f'final reviewer metrics must be pinned to {METRICS_COMMIT}')
    if flow_metrics.get('parameters') != final_metrics_parameters():
        error(
            errors,
            'final reviewer metrics must request exactly '
            f'{list(FINAL_METRICS)} via --metric; empty/default all and additional '
            'metrics, including mutual information, are forbidden',
        )


def validate_coverage_manifest(config_dir: Path, errors: list[str]) -> None:
    manifest_path = config_dir / 'coverage/gatemeclass/cases.tsv'
    if not manifest_path.exists():
        relative_path = manifest_path.relative_to(config_dir)
        error(errors, f'missing GateMeClass coverage manifest: {relative_path}')
        return

    with manifest_path.open(newline='') as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))

    required_columns = {
        'dataset',
        'fold',
        'drop_ungated_training',
        'drop_ungated_test',
        'gmm_parameterization',
        'status',
        'validation_status',
        'process_returncode',
        'runner_commit',
        'output_archive_sha256',
    }
    if not rows or not required_columns.issubset(rows[0]):
        error(errors, 'GateMeClass coverage manifest has missing columns')
        return

    keys = [
        (
            row['dataset'],
            row['fold'],
            row['drop_ungated_training'],
            row['drop_ungated_test'],
            row['gmm_parameterization'],
        )
        for row in rows
    ]
    expected_keys = {
        (dataset, str(fold), str(drop_train).lower(), str(drop_test).lower(), gmm)
        for dataset in ('FR-FCM-Z238', 'FR-FCM-Z3YR', 'FR-FCM-Z2KP-covid', 'FlowCyt')
        for fold in range(1, 6)
        for drop_train, drop_test in ((False, False), (True, False), (True, True))
        for gmm in ('E', 'V')
    }
    if set(keys) != expected_keys or len(rows) != len(expected_keys):
        error(
            errors,
            'GateMeClass coverage manifest must contain the exact 120 planned cases',
        )

    counts = Counter(row['status'] for row in rows)
    if counts != EXPECTED_COVERAGE_COUNTS:
        error(errors, f'GateMeClass coverage counts differ: {dict(counts)}')

    dataset_status_counts = Counter((row['dataset'], row['status']) for row in rows)
    if dataset_status_counts != EXPECTED_DATASET_STATUS_COUNTS:
        error(errors, 'GateMeClass per-dataset coverage counts differ')

    passed_runner_counts = Counter(
        row['runner_commit'] for row in rows if row['status'] == 'passed'
    )
    if passed_runner_counts != EXPECTED_PASSED_RUNNER_COUNTS:
        error(errors, 'GateMeClass passed-case runner provenance differs')

    for row, key in zip(rows, keys):
        case = '/'.join(str(value) for value in key)
        output_sha = row['output_archive_sha256']
        if row['status'] == 'passed':
            if (
                row['validation_status'] != 'PASS'
                or row['process_returncode'] != '0'
                or not re.fullmatch(r'[0-9a-f]{64}', output_sha)
            ):
                error(
                    errors,
                    f'passed GateMeClass case lacks validated output provenance: {case}',
                )
        elif output_sha != 'NA':
            error(
                errors,
                f'non-passing GateMeClass case must not identify a prediction: {case}',
            )
        if row['status'] == 'timed_out' and row['process_returncode'] != '124':
            error(errors, f'GateMeClass timeout has unexpected return code: {case}')
        if row['status'] == 'interrupted' and row['process_returncode'] != '-15':
            error(errors, f'GateMeClass interruption has unexpected return code: {case}')
        if any(value.startswith('/') for value in row.values() if value):
            error(errors, f'GateMeClass coverage manifest contains an absolute path: {case}')


def validate_reviewer_policy(
    config_path: Path,
    data: dict[str, Any],
    stages: dict[str, dict[str, Any]],
    environments: dict[str, Any],
    errors: list[str],
) -> None:
    if (
        config_path.name not in {FINAL_CONFIG, INVESTIGATIVE_CONFIG}
        or 'analysis' not in stages
    ):
        return

    analysis_modules = modules_by_id(stages['analysis'])
    if config_path.name == FINAL_CONFIG:
        validate_final_metrics(stages.get('metrics', {}), errors)
        if set(analysis_modules) != FINAL_MODELS:
            error(
                errors,
                f'final reviewer config must contain exactly these models: {sorted(FINAL_MODELS)}',
            )
        if 'gatemeclass' in environments:
            error(errors, 'final reviewer config must not contain the unused GateMeClass environment')

        investigative_path = config_path.with_name(INVESTIGATIVE_CONFIG)
        if not investigative_path.exists():
            error(errors, f'final reviewer config requires {INVESTIGATIVE_CONFIG}')
        else:
            expected = load_config(investigative_path)
            expected['description'] = data.get('description')
            expected.get('software_environments', {}).pop('gatemeclass', None)
            expected_analysis = find_stage(expected, 'analysis')
            expected_analysis['modules'] = [
                module
                for module in expected_analysis.get('modules', [])
                if module.get('id') != 'gatemeclass'
            ]
            expected_metrics = modules_by_id(find_stage(expected, 'metrics'))
            expected_metrics['flow_metrics']['parameters'] = final_metrics_parameters()
            if data != expected:
                error(
                    errors,
                    'final reviewer config must differ from the investigative config '
                    'only by its description, GateMeClass removal, and approved metrics request',
                )
        validate_coverage_manifest(config_path.parent, errors)
    else:
        gatemeclass = analysis_modules.get('gatemeclass')
        if not gatemeclass:
            error(errors, 'investigative reviewer config must retain GateMeClass')
        elif gatemeclass.get('repository', {}).get('commit') != GATEMECLASS_COMMIT:
            error(errors, f'investigative GateMeClass must be pinned to {GATEMECLASS_COMMIT}')

    dgcytof = analysis_modules.get('dgcytof', {})
    if dgcytof.get('repository', {}).get('commit') != DGCYTOF_COMMIT:
        error(errors, f'reviewer DGCyTOF must be pinned to {DGCYTOF_COMMIT}')


def validate(config_path: Path) -> list[str]:
    data = load_config(config_path)
    errors: list[str] = []

    for key in ['software_environments', 'stages', 'metric_collectors']:
        if key not in data:
            error(errors, f'missing top-level key: {key}')

    environments = data.get('software_environments', {})
    if not isinstance(environments, dict):
        error(errors, 'software_environments must be a mapping')
        environments = {}

    for env_id, env in environments.items():
        conda_path = env.get('conda') if isinstance(env, dict) else None
        if not conda_path:
            error(errors, f'software environment {env_id} is missing conda path')
        elif not (config_path.parent / conda_path).exists():
            error(errors, f'software environment {env_id} references missing file: {conda_path}')

    required_stages = ['data', 'preprocessing', 'stratify', 'analysis', 'metrics']
    stages = {
        stage.get('id'): stage
        for stage in data.get('stages', [])
        if isinstance(stage, dict)
    }
    for stage_id in required_stages:
        if stage_id not in stages:
            error(errors, f'missing required stage: {stage_id}')

    for stage_id, stage in stages.items():
        seen_modules: set[str] = set()
        for module in stage.get('modules', []):
            module_id = module.get('id')
            if not module_id:
                error(errors, f'stage {stage_id} has module without id')
                continue
            if module_id in seen_modules:
                error(errors, f'stage {stage_id} has duplicate module id: {module_id}')
            seen_modules.add(module_id)

            env_id = module.get('software_environment')
            if env_id and env_id not in environments:
                error(
                    errors,
                    f'module {stage_id}.{module_id} references unknown '
                    f'software_environment: {env_id}',
                )

            repository = module.get('repository')
            if repository:
                url = repository.get('url')
                commit = repository.get('commit')
                if not url:
                    error(errors, f'module {stage_id}.{module_id} repository missing url')
                if not commit:
                    error(errors, f'module {stage_id}.{module_id} repository missing commit')
                elif not SHA_RE.match(str(commit)):
                    error(errors, f'module {stage_id}.{module_id} commit does not look like a SHA: {commit}')

    if 'data' in stages:
        ids = output_ids(stages['data'])
        missing = {'data.raw', 'data.import_metadata'} - ids
        if missing:
            error(errors, f"data stage missing outputs: {', '.join(sorted(missing))}")

        data_import = None
        for module in stages['data'].get('modules', []):
            if module.get('id') == 'data_import':
                data_import = module
                break
        if data_import:
            seen_values: set[tuple[str, ...]] = set()
            for parameter in data_import.get('parameters', []):
                values = tuple(str(value) for value in parameter.get('values', []))
                if values in seen_values:
                    error(errors, f'duplicate exact data_import parameter block: {values}')
                seen_values.add(values)

    if 'analysis' in stages:
        ids = output_ids(stages['analysis'])
        if 'analysis.prediction' not in ids:
            error(errors, 'analysis stage missing output: analysis.prediction')

    if 'metrics' in stages:
        ids = output_ids(stages['metrics'])
        if 'metrics.scores' not in ids:
            error(errors, 'metrics stage missing output: metrics.scores')

    validate_reviewer_policy(config_path, data, stages, environments, errors)

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='Clustering_conda.yml')
    parser.add_argument(
        '--all',
        action='store_true',
        help='validate every Clustering_conda*.yml config',
    )
    args = parser.parse_args()
    config_paths = (
        sorted(Path('.').glob('Clustering_conda*.yml'))
        if args.all
        else [Path(args.config)]
    )
    failed = False
    for config_path in config_paths:
        errors = validate(config_path)
        if errors:
            failed = True
            print(f'{config_path} validation failed:')
            for item in errors:
                print(f'- {item}')
        else:
            print(f'{config_path} is valid')
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
