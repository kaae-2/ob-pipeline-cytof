#!/usr/bin/env python3
"""Bootstrap a local Omnibenchmark environment and dry-run the benchmark."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path


MINIFORGE_URL = 'https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh'


def prompt_bool(text: str, default: bool = False) -> bool:
    marker = 'Y/n' if default else 'y/N'
    value = input(f'{text} [{marker}]: ').strip().lower()
    if not value:
        return default
    return value in {'y', 'yes', 'true', '1'}


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print(f'+ {" ".join(command)}')
    subprocess.run(command, check=True, env=env)


def conda_executable(prefix: Path | None) -> str | None:
    found = shutil.which('conda')
    if found:
        return found
    if prefix:
        candidate = prefix / 'bin' / 'conda'
        if candidate.exists():
            return str(candidate)
    default = Path.home() / 'miniforge3' / 'bin' / 'conda'
    if default.exists():
        return str(default)
    return None


def install_miniforge(prefix: Path, yes: bool) -> str:
    if not yes and not prompt_bool(f'Download and install Miniforge to {prefix}?', False):
        raise SystemExit('Conda is required. Re-run after installing conda or approve Miniforge installation.')
    prefix.parent.mkdir(parents=True, exist_ok=True)
    installer = Path('/tmp/opencode/Miniforge3-Linux-x86_64.sh')
    installer.parent.mkdir(parents=True, exist_ok=True)
    print(f'Downloading {MINIFORGE_URL} to {installer}')
    urllib.request.urlretrieve(MINIFORGE_URL, installer)
    run(['bash', str(installer), '-b', '-p', str(prefix)])
    return str(prefix / 'bin' / 'conda')


def env_exists(conda: str, env_name: str) -> bool:
    result = subprocess.run([conda, 'env', 'list'], check=True, text=True, capture_output=True)
    return any(line.split() and line.split()[0] == env_name for line in result.stdout.splitlines())


def ensure_env(conda: str, env_name: str, yes: bool) -> None:
    if env_exists(conda, env_name):
        print(f'Conda env {env_name} already exists')
        return
    if not yes and not prompt_bool(f'Create conda env {env_name} with Python 3.11?', True):
        raise SystemExit(f'Conda env {env_name} is required.')
    run([conda, 'create', '-n', env_name, 'python=3.11', '-y'])


def conda_run(conda: str, env_name: str, command: list[str], env: dict[str, str]) -> None:
    run([conda, 'run', '-n', env_name, '--no-capture-output', *command], env=env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-name', default='omnibenchmark')
    parser.add_argument('--conda-prefix', default=str(Path.home() / 'miniforge3'))
    parser.add_argument('--benchmark-yaml', default='Clustering_conda.yml')
    parser.add_argument('--tmpdir', default=str(Path.home() / 'tmp'))
    parser.add_argument('--conda-pkgs-dir', default=str(Path.home() / 'conda-pkgs'))
    parser.add_argument('--skip-dry-run', action='store_true')
    parser.add_argument('--yes', action='store_true', help='Approve conda install/env creation prompts')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    conda_prefix = Path(args.conda_prefix).expanduser()
    conda = conda_executable(conda_prefix)
    if not conda:
        conda = install_miniforge(conda_prefix, args.yes)

    ensure_env(conda, args.env_name, args.yes)
    env = os.environ.copy()
    env['TMPDIR'] = str(Path(args.tmpdir).expanduser())
    env['TMP'] = env['TMPDIR']
    env['TEMP'] = env['TMPDIR']
    env['CONDA_PKGS_DIRS'] = str(Path(args.conda_pkgs_dir).expanduser())
    Path(env['TMPDIR']).mkdir(parents=True, exist_ok=True)
    Path(env['CONDA_PKGS_DIRS']).mkdir(parents=True, exist_ok=True)

    conda_run(conda, args.env_name, ['python', '-m', 'pip', 'install', '--upgrade', 'pip'], env)
    conda_run(conda, args.env_name, ['python', '-m', 'pip', 'install', 'omnibenchmark', 'just', 'pyyaml'], env)
    conda_run(conda, args.env_name, ['python', 'scripts/validate_benchmark_config.py', '--config', args.benchmark_yaml], env)

    if args.skip_dry_run:
        print('Skipping dry-run by request.')
        return
    conda_run(conda, args.env_name, ['ob', 'run', 'benchmark', '-b', args.benchmark_yaml, '--local-storage', '--dry-run'], env)
    print('Bootstrap complete: benchmark dry-run succeeded.')


if __name__ == '__main__':
    main()
