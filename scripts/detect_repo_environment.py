#!/usr/bin/env python3
"""Detect model repository language and generate benchmark env files."""

from __future__ import annotations

from pathlib import Path

from github import GitHubRepo, list_tree, read_text_file


def detect_project(repo: GitHubRepo, ref: str) -> dict[str, object]:
    paths = {item.get('path', '') for item in list_tree(repo, ref) if item.get('type') == 'blob'}
    lower_paths = {path.lower(): path for path in paths}
    signals: list[str] = []

    python_files = ['environment.yml', 'environment.yaml', 'conda.yml', 'requirements.txt', 'pyproject.toml', 'setup.py', 'setup.cfg']
    r_files = ['DESCRIPTION', 'renv.lock', 'install.R', 'requirements.R']
    bash_files = ['run.sh', 'entrypoint.sh']

    language = 'bash'
    for filename in python_files:
        if filename.lower() in lower_paths:
            signals.append(lower_paths[filename.lower()])
            language = 'python'
    for filename in r_files:
        if filename.lower() in lower_paths:
            signals.append(lower_paths[filename.lower()])
            language = 'r' if language == 'bash' else 'mixed'
    for filename in bash_files:
        if filename.lower() in lower_paths:
            signals.append(lower_paths[filename.lower()])

    if any(path.endswith('.R') for path in paths) and language == 'bash':
        language = 'r'
    if any(path.endswith('.py') for path in paths) and language == 'bash':
        language = 'python'

    return {'language': language, 'signals': sorted(set(signals)), 'paths': paths}


def generate_env_yaml(repo: GitHubRepo, ref: str, env_id: str, language: str) -> str:
    if language == 'python' or language == 'mixed':
        requirements = read_text_file(repo, 'requirements.txt', ref)
        pip_lines = []
        if requirements:
            pip_lines = [line.strip() for line in requirements.splitlines() if line.strip() and not line.strip().startswith('#')]
        lines = [
            f'name: {env_id}',
            'channels:',
            '  - conda-forge',
            'dependencies:',
            '  - python=3.11',
            '  - pip',
            '  - numpy',
            '  - pandas',
        ]
        if pip_lines:
            lines.append('  - pip:')
            lines.extend(f'      - {line}' for line in pip_lines)
        else:
            lines.append('  - pip:')
            lines.append('      - .')
        return '\n'.join(lines) + '\n'

    if language == 'r':
        return '\n'.join([
            f'name: {env_id}',
            'channels:',
            '  - conda-forge',
            'dependencies:',
            '  - r-base',
            '  - r-essentials',
            '  - r-jsonlite',
            '  - r-data.table',
            '  - r-optparse',
        ]) + '\n'

    return '\n'.join([
        f'name: {env_id}',
        'channels:',
        '  - conda-forge',
        'dependencies:',
        '  - bash',
        '  - coreutils',
        '  - tar',
        '  - gzip',
        '  - zstd',
    ]) + '\n'


def write_env_file(path: str | Path, content: str) -> None:
    env_path = Path(path)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if env_path.exists():
        raise FileExistsError(f'{env_path} already exists')
    env_path.write_text(content, encoding='utf-8')
