#!/usr/bin/env python3
"""Interactively add an analysis model to Clustering_conda.yml."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmark_config import (
    add_software_environment,
    choose,
    find_stage,
    load_config,
    normalize_id,
    parse_parameter_values,
    prompt,
    prompt_bool,
    save_config,
)
from detect_repo_environment import detect_project, generate_env_yaml, write_env_file
from github import parse_github_repo, resolve_ref


MODEL_CONTRACT = '''
Model module implementation contract

Your repository must expose a command that accepts:
- --name <model id/name>
- --output_dir <output directory>
- --data.train_matrix <tar.gz>
- --data.train_labels <tar.gz>
- --data.test_matrix <tar.gz>
- --data.metadata <metadata.json.gz>

Required output:
- ${output_dir}/${name}_predicted_labels.tar.gz

The prediction tarball must contain predicted labels for every test sample in
the same sample identity space as data.test_matrix.
'''.strip()


def collect_parameter_sets(raw_parameter: list[str] | None) -> list[dict[str, list[str]]]:
    if raw_parameter:
        return [{'values': parse_parameter_values(value)} for value in raw_parameter]

    if not prompt_bool('Add model parameters?', False):
        return []

    parameter_sets: list[dict[str, list[str]]] = []
    while True:
        raw = prompt('Parameter values, e.g. --k 20 --sampling 0.1')
        values = parse_parameter_values(raw)
        if values:
            parameter_sets.append({'values': values})
        if not prompt_bool('Add another parameter set?', False):
            break
    return parameter_sets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='Clustering_conda.yml')
    parser.add_argument('--repository-url')
    parser.add_argument('--ref', default='main')
    parser.add_argument('--commit')
    parser.add_argument('--id')
    parser.add_argument('--name')
    parser.add_argument('--software-environment')
    parser.add_argument('--environment-type', choices=['python', 'r', 'bash', 'existing'])
    parser.add_argument('--env-path')
    parser.add_argument('--parameter', action='append', help='One parameter set, e.g. "--k 20". Repeatable.')
    parser.add_argument('--yes', action='store_true')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    data = load_config(config_path)
    analysis_stage = find_stage(data, 'analysis')

    repo_url = args.repository_url or prompt('GitHub repository URL')
    repo = parse_github_repo(repo_url)
    ref = args.ref or prompt('Branch/ref to inspect', 'main')
    commit = args.commit or resolve_ref(repo, ref)

    detection = detect_project(repo, ref)
    detected_language = str(detection['language'])
    signals = detection.get('signals', [])
    print(f'Detected project type: {detected_language}')
    if signals:
        print('Detected setup files:')
        for signal in signals:
            print(f'- {signal}')

    model_id = normalize_id(args.id or prompt('Model id', repo.name))
    existing_ids = {module.get('id') for module in analysis_stage.get('modules', [])}
    if model_id in existing_ids:
        raise ValueError(f'analysis module already exists: {model_id}')

    display_name = args.name or prompt('Display name', model_id)
    env_id = normalize_id(args.software_environment or prompt('Software environment id', model_id))
    environments = data.setdefault('software_environments', {})

    if env_id not in environments:
        env_type = args.environment_type
        if not env_type:
            env_type = choose('Choose environment type:', ['python', 'r', 'bash', 'existing'])
        if env_type == 'existing':
            if env_id not in environments:
                raise ValueError(f'software environment does not exist: {env_id}')
        else:
            env_path = args.env_path or prompt('Conda env path', f'envs/{env_id}.yml')
            if args.yes or prompt_bool(f'Generate {env_type} environment at {env_path}?', True):
                content = generate_env_yaml(repo, ref, env_id, env_type)
                write_env_file(env_path, content)
                print(f'Wrote {env_path}')
            add_software_environment(data, env_id, f'{display_name} environment', env_path)

    parameter_sets = collect_parameter_sets(args.parameter)
    module = {
        'id': model_id,
        'name': display_name,
        'software_environment': env_id,
        'repository': {'url': repo_url, 'commit': commit},
        'parameters': parameter_sets,
    }
    analysis_stage.setdefault('modules', []).append(module)
    save_config(config_path, data)

    print(f'Added analysis module {model_id} to {config_path}')
    print()
    print(MODEL_CONTRACT)
    print('\nNext steps:')
    print('1. Review: git diff Clustering_conda.yml envs/')
    print('2. Validate: just validate-config')
    print('3. Dry-run: just dry-run')


if __name__ == '__main__':
    main()
