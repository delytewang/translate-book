#!/usr/bin/env python3
"""
build_glossary.py - Normalize agent-produced glossary candidates into the
canonical glossary.json v2 schema used by translate-book.

This keeps agents out of the final on-disk schema. They can propose simple
term candidates, while this script owns ids, defaults, validation, and the
final glossary.json write.
"""

import argparse
import json
import os
from pathlib import Path

import glossary as glossary_mod


def _load_candidates(path):
    with open(path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Glossary candidates at {path} are not valid JSON: {e}") from e

    if isinstance(data, list):
        terms = data
        top_n = glossary_mod.DEFAULT_TOP_N
    elif isinstance(data, dict):
        terms = data.get('terms')
        top_n = data.get('high_frequency_top_n', glossary_mod.DEFAULT_TOP_N)
    else:
        raise ValueError(
            f"Glossary candidates at {path} must be a JSON array or object, "
            f"got {type(data).__name__}"
        )

    if not isinstance(terms, list):
        raise ValueError(f"Glossary candidates at {path} must contain a 'terms' array")
    if isinstance(top_n, bool) or not isinstance(top_n, int):
        raise ValueError(
            f"Glossary candidates at {path}: 'high_frequency_top_n' must be an integer, "
            f"got {type(top_n).__name__}"
        )

    return terms, top_n


def _normalize_aliases(raw_aliases, idx, path):
    if raw_aliases is None:
        return []
    if isinstance(raw_aliases, str):
        raw_aliases = [raw_aliases]
    if not isinstance(raw_aliases, list):
        raise ValueError(
            f"Glossary candidate #{idx} in {path}: 'aliases' must be a list or string, "
            f"got {type(raw_aliases).__name__}"
        )

    aliases = []
    seen = set()
    for alias in raw_aliases:
        if not isinstance(alias, str):
            raise ValueError(
                f"Glossary candidate #{idx} in {path}: every alias must be a string, "
                f"got {type(alias).__name__}"
            )
        cleaned = alias.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        aliases.append(cleaned)
    return aliases


def _candidate_field(candidate, idx, path, *names, required=False, default=''):
    for name in names:
        if name in candidate:
            value = candidate[name]
            break
    else:
        if required:
            joined = ' / '.join(repr(name) for name in names)
            raise ValueError(
                f"Glossary candidate #{idx} in {path} missing required field {joined}"
            )
        return default

    if not isinstance(value, str):
        raise ValueError(
            f"Glossary candidate #{idx} in {path}: field {name!r} must be a string, "
            f"got {type(value).__name__}"
        )
    return value.strip()


def _normalize_terms(candidates, path):
    normalized = []
    seen_sources = set()

    for idx, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(
                f"Glossary candidate #{idx} in {path} must be an object, "
                f"got {type(candidate).__name__}"
            )

        source = _candidate_field(
            candidate, idx, path, 'source', 'term', required=True
        )
        target = _candidate_field(
            candidate, idx, path, 'target', 'translation', required=True
        )
        category = _candidate_field(candidate, idx, path, 'category', default='')
        notes = _candidate_field(candidate, idx, path, 'notes', default='')
        aliases = _normalize_aliases(candidate.get('aliases'), idx, path)

        if not source:
            raise ValueError(f"Glossary candidate #{idx} in {path}: 'source' cannot be empty")
        if not target:
            raise ValueError(f"Glossary candidate #{idx} in {path}: 'target' cannot be empty")
        if source in seen_sources:
            raise ValueError(
                f"Glossary candidates at {path}: duplicate source {source!r}. "
                "Merge duplicates before building glossary.json."
            )
        seen_sources.add(source)

        aliases = [alias for alias in aliases if alias != source]
        term = {
            'id': source,
            'source': source,
            'target': target,
            'category': category,
            'aliases': aliases,
            'gender': 'unknown',
            'confidence': 'medium',
            'frequency': 0,
            'evidence_refs': [],
            'notes': notes,
        }
        normalized.append(term)

    return normalized


def build_glossary(temp_dir, candidates_path):
    terms, top_n = _load_candidates(candidates_path)
    glossary = {
        'version': glossary_mod.GLOSSARY_SCHEMA_VERSION,
        'terms': _normalize_terms(terms, candidates_path),
        'high_frequency_top_n': top_n,
        'applied_meta_hashes': {},
    }
    output_path = os.path.join(temp_dir, 'glossary.json')
    glossary_mod.save_glossary(output_path, glossary)
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Build canonical glossary.json from agent-produced candidate JSON"
    )
    parser.add_argument('temp_dir', help="Path to <book>_temp/ directory")
    parser.add_argument(
        'candidates_path',
        help="Path to a candidate JSON file (array or {terms:[...]} object)",
    )
    args = parser.parse_args()

    output_path = build_glossary(args.temp_dir, args.candidates_path)
    print(Path(output_path).resolve())


if __name__ == '__main__':
    main()
