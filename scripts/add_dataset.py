#!/usr/bin/env python3
"""Interactively add a dataset source to Clustering_conda.yml."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmark_config import (
    add_software_environment,
    append_parameter_set,
    choose,
    find_module,
    find_stage,
    load_config,
    normalize_id,
    prompt,
    prompt_bool,
    save_config,
)
from detect_repo_environment import print_config_cfg_warning
from github import discover_prepared_datasets, parse_github_repo, resolve_ref


DATASET_MODULE_CONTRACT = '''
Dataset module implementation contract

Your repository must expose a command that Omnibenchmark can run with:
- --name <output name>
- --output_dir <output directory>

Recommended dataset-specific arguments:
- --dataset_name <dataset id>
- --seed <seed>

Required outputs:
- ${output_dir}/${name}.data.tar.gz
- ${output_dir}/${dataset}.${name}.metadata.json.gz

The data tarball must contain the matrix/label files expected by the downstream
preprocessing module. Use stable sample identifiers and keep feature/channel
names consistent across train/test materialization.

The metadata JSON must include enough information for downstream preprocessing,
metrics, and collector de-duplication, including:
- dataset_name
- sample identifiers
- feature/channel names
- label/population metadata or label mapping information
- batch metadata if available
- cross-validation/wrapped-run identifiers if the module creates them

This benchmark wires downstream stages by output ids. Every data module must
emit these ids:
- data.raw
- data.import_metadata
'''.strip()


def build_data_import_values(args: argparse.Namespace, dataset_name: str | None = None) -> list[str]:
    name = args.name or 'data_import.data_raw'
    values = [
        '--dataset_name', dataset_name or args.dataset_name,
        '--seed', str(args.seed or '42'),
    ]
    if args.sub_sampling:
        values.extend(['--sub-sampling', str(args.sub_sampling)])
    values.extend([
        '--transformation-cofactor', str(args.transformation_cofactor or '150'),
        '--potential-batches', str(args.potential_batches or '1'),
        '--name', name,
    ])
    return values


def add_existing_data_import(config_path: Path, args: argparse.Namespace) -> None:
    data = load_config(config_path)
    data_stage = find_stage(data, 'data')
    data_import = find_module(data_stage, 'data_import')

    dataset_name = args.dataset_name
    if not dataset_name:
        print('Loading prepared datasets from github.com/kaae-2/ob-flow-datasets ...')
        datasets = discover_prepared_datasets()
        dataset_name = choose('Available data_import datasets:', datasets)

    values = build_data_import_values(args, dataset_name)
    append_parameter_set(data_import, values)
    save_config(config_path, data)
    print(f'Added data_import parameter set for {dataset_name} to {config_path}')


def add_external_dataset_module(config_path: Path, args: argparse.Namespace) -> None:
    data = load_config(config_path)
    data_stage = find_stage(data, 'data')

    module_id = normalize_id(args.module_id or prompt('Dataset module id'))
    if module_id in {module.get('id') for module in data_stage.get('modules', [])}:
        raise ValueError(f'data module already exists: {module_id}')

    display_name = args.display_name or prompt('Display name', module_id)
    repo_url = args.repository_url or prompt('GitHub repository URL')
    repo = parse_github_repo(repo_url)
    ref = args.ref or prompt('Branch/ref to pin', 'main')
    commit = args.commit or resolve_ref(repo, ref)
    print_config_cfg_warning(repo, ref)
    env_id = normalize_id(args.software_environment or prompt('Software environment id', 'py'))
    output_name = args.name or prompt('Output basename', 'data_raw')
    dataset_name = args.dataset_name or prompt('Dataset name/id')

    if env_id not in data.get('software_environments', {}):
        conda_path = prompt('Conda env path', f'envs/{env_id}.yml')
        add_software_environment(data, env_id, f'{display_name} environment', conda_path)

    values = ['--dataset_name', dataset_name, '--name', output_name]
    if args.seed:
        values.extend(['--seed', str(args.seed)])

    module = {
        'id': module_id,
        'name': display_name,
        'software_environment': env_id,
        'repository': {'url': repo_url, 'commit': commit},
        'parameters': [{'values': values}],
    }
    data_stage.setdefault('modules', []).append(module)
    save_config(config_path, data)

    print(f'Added external dataset module {module_id} to {config_path}')
    print()
    print(DATASET_MODULE_CONTRACT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='Clustering_conda.yml')
    parser.add_argument('--mode', choices=['data-import', 'external-module'])
    parser.add_argument('--dataset-name')
    parser.add_argument('--seed')
    parser.add_argument('--transformation-cofactor')
    parser.add_argument('--potential-batches')
    parser.add_argument('--sub-sampling')
    parser.add_argument('--name')
    parser.add_argument('--module-id')
    parser.add_argument('--display-name')
    parser.add_argument('--repository-url')
    parser.add_argument('--ref')
    parser.add_argument('--commit')
    parser.add_argument('--software-environment')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    mode = args.mode
    if not mode:
        mode = choose('How should this dataset be added?', [
            'data-import',
            'external-module',
        ])

    if mode == 'data-import':
        if not args.seed:
            args.seed = prompt('Seed', '42')
        if not args.transformation_cofactor:
            args.transformation_cofactor = prompt('Transformation cofactor', '150')
        if not args.potential_batches:
            args.potential_batches = prompt('Potential batches', '1')
        if not args.sub_sampling and prompt_bool('Add sub-sampling?', False):
            args.sub_sampling = prompt('Sub-sampling rows')
        add_existing_data_import(config_path, args)
    else:
        add_external_dataset_module(config_path, args)

    print('\nNext steps:')
    print('1. Review: git diff Clustering_conda.yml')
    print('2. Validate: just validate-config')
    print('3. Dry-run: just dry-run')


if __name__ == '__main__':
    main()
