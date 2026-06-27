#!/usr/bin/env python3
"""Small GitHub API helpers used by benchmark scaffolding scripts."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


GITHUB_API = 'https://api.github.com'


@dataclass(frozen=True)
class GitHubRepo:
    owner: str
    name: str

    @property
    def slug(self) -> str:
        return f'{self.owner}/{self.name}'


def parse_github_repo(url_or_slug: str) -> GitHubRepo:
    value = url_or_slug.strip().removesuffix('.git')
    if re.fullmatch(r'[^/]+/[^/]+', value):
        owner, name = value.split('/', 1)
        return GitHubRepo(owner, name)
    parsed = urllib.parse.urlparse(value)
    if parsed.netloc not in {'github.com', 'www.github.com'}:
        raise ValueError('repository must be a GitHub URL or owner/repo slug')
    parts = [part for part in parsed.path.split('/') if part]
    if len(parts) < 2:
        raise ValueError('GitHub URL must include owner and repository')
    return GitHubRepo(parts[0], parts[1])


def api_get(path: str) -> Any:
    request = urllib.request.Request(f'{GITHUB_API}{path}')
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if token:
        request.add_header('Authorization', f'Bearer {token}')
    request.add_header('Accept', 'application/vnd.github+json')
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as error:
        body = error.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'GitHub API error {error.code} for {path}: {body}') from error


def resolve_ref(repo: GitHubRepo, ref: str) -> str:
    data = api_get(f'/repos/{repo.slug}/commits/{urllib.parse.quote(ref, safe="")}')
    sha = data.get('sha')
    if not sha:
        raise RuntimeError(f'could not resolve ref {ref} in {repo.slug}')
    return sha


def list_tree(repo: GitHubRepo, ref: str = 'main') -> list[dict[str, Any]]:
    sha = resolve_ref(repo, ref)
    data = api_get(f'/repos/{repo.slug}/git/trees/{sha}?recursive=1')
    tree = data.get('tree')
    if not isinstance(tree, list):
        raise RuntimeError(f'could not read tree for {repo.slug}@{ref}')
    return tree


def read_text_file(repo: GitHubRepo, path: str, ref: str = 'main') -> str | None:
    quoted_path = urllib.parse.quote(path, safe='/')
    quoted_ref = urllib.parse.quote(ref, safe='')
    try:
        data = api_get(f'/repos/{repo.slug}/contents/{quoted_path}?ref={quoted_ref}')
    except RuntimeError:
        return None
    content = data.get('content')
    encoding = data.get('encoding')
    if not content or encoding != 'base64':
        return None
    return base64.b64decode(content).decode('utf-8', errors='replace')


def discover_prepared_datasets(ref: str = 'main') -> list[str]:
    repo = GitHubRepo('kaae-2', 'ob-flow-datasets')
    tree = list_tree(repo, ref)
    datasets: set[str] = set()
    for item in tree:
        path = item.get('path', '')
        parts = path.split('/')
        if len(parts) >= 3 and parts[0] == 'prepared' and item.get('type') in {'tree', 'blob'}:
            datasets.add(parts[2])
    return sorted(datasets)
