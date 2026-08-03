#!/usr/bin/env python3
"""Validate the benchmark YAML shape used by the helper scripts."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from benchmark_config import load_config


SHA_RE = re.compile(r'^[0-9a-fA-F]{7,40}$')


def error(errors: list[str], message: str) -> None:
    errors.append(message)


def output_ids(module_or_stage: dict[str, Any]) -> set[str]:
    return {
        output.get('id')
        for output in module_or_stage.get('outputs', [])
        if output.get('id')
    }


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
