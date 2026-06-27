#!/usr/bin/env python3
"""Shared helpers for editing Omnibenchmark YAML configs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


Config = dict[str, Any]


def load_config(path: str | Path) -> Config:
    with Path(path).open('r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f'{path} did not parse as a YAML mapping')
    return data


def save_config(path: str | Path, data: Config) -> None:
    with Path(path).open('w', encoding='utf-8') as handle:
        yaml.safe_dump(data, handle, sort_keys=False, width=1000)


def find_stage(data: Config, stage_id: str) -> dict[str, Any]:
    for stage in data.get('stages', []):
        if stage.get('id') == stage_id:
            return stage
    raise ValueError(f'missing stage: {stage_id}')


def find_module(stage: dict[str, Any], module_id: str) -> dict[str, Any]:
    for module in stage.get('modules', []):
        if module.get('id') == module_id:
            return module
    raise ValueError(f"missing module '{module_id}' in stage '{stage.get('id')}'")


def module_ids(stage: dict[str, Any]) -> set[str]:
    return {module.get('id') for module in stage.get('modules', []) if module.get('id')}


def ensure_module_outputs(module: dict[str, Any], outputs: list[dict[str, str]]) -> None:
    existing = {output.get('id') for output in module.get('outputs', [])}
    for output in outputs:
        if output.get('id') not in existing:
            module.setdefault('outputs', []).append(output)


def data_output_contract(name: str = 'data_raw') -> list[dict[str, str]]:
    return [
        {
            'id': 'data.raw',
            'path': f'{{input}}/{{stage}}/{{module}}/{{params}}/{name}.data.tar.gz',
        },
        {
            'id': 'data.import_metadata',
            'path': f'{{input}}/{{stage}}/{{module}}/{{params}}/{{dataset}}.{name}.metadata.json.gz',
        },
    ]


def add_software_environment(
    data: Config,
    env_id: str,
    description: str,
    conda_path: str,
    envmodule: str | None = None,
) -> None:
    environments = data.setdefault('software_environments', {})
    if env_id in environments:
        return
    environments[env_id] = {
        'description': description,
        'conda': conda_path,
        'envmodule': envmodule or env_id,
    }


def append_parameter_set(module: dict[str, Any], values: list[str]) -> None:
    parameters = module.setdefault('parameters', [])
    if {'values': values} in parameters:
        raise ValueError('exact parameter set already exists')
    parameters.append({'values': values})


def parameter_value(values: list[Any], flag: str) -> str | None:
    try:
        index = values.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(values):
        return None
    return str(values[index + 1])


def normalize_id(value: str) -> str:
    normalized = value.strip().lower().replace('_', '-').replace(' ', '-')
    normalized = ''.join(char for char in normalized if char.isalnum() or char == '-')
    if not normalized:
        raise ValueError('id cannot be empty')
    return normalized


def prompt(text: str, default: str | None = None) -> str:
    suffix = f' [{default}]' if default is not None else ''
    value = input(f'{text}{suffix}: ').strip()
    if not value and default is not None:
        return default
    return value


def prompt_bool(text: str, default: bool = True) -> bool:
    marker = 'Y/n' if default else 'y/N'
    value = input(f'{text} [{marker}]: ').strip().lower()
    if not value:
        return default
    return value in {'y', 'yes', 'true', '1'}


def choose(text: str, options: list[str]) -> str:
    if not options:
        raise ValueError('no options available')
    print(text)
    for index, option in enumerate(options, start=1):
        print(f'{index}. {option}')
    while True:
        raw = input('Select number: ').strip()
        try:
            selected = int(raw)
        except ValueError:
            print('Enter a number from the list.')
            continue
        if 1 <= selected <= len(options):
            return options[selected - 1]
        print('Selection out of range.')


def parse_parameter_values(raw: str) -> list[str]:
    return [part for part in raw.split() if part]
