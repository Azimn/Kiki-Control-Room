"""Read-only complexity and improvement assessment for Kiki (no model required)."""
from __future__ import annotations
import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import re

CODE = {'.py', '.js', '.cjs', '.mjs', '.ts', '.tsx', '.jsx', '.gs', '.html', '.css'}
DOC = {'.md', '.rst'}
CONFIG = {'.yml', '.yaml', '.toml', '.json', '.ini', '.cfg', '.cmd', '.sh'}
SKIP = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache',
        '.mypy_cache', 'dist', 'build', 'coverage', '.next', 'audit-output', '.prior'}
TEST_CALL = re.compile(r'\b(?:test|it)\s*\(')
MARKER = re.compile(r'\b(?:TODO|FIXME|HACK)\b')

def _counts(path: Path) -> tuple[int, int, int]:
    try:
        if path.stat().st_size > 1_000_000:
            return 0, 0, 0
        content = path.read_text(encoding='utf-8')
    except (UnicodeError, OSError):
        return 0, 0, 0
    loc = sum(bool(line.strip()) for line in content.splitlines())
    if path.suffix == '.py':
        try:
            tree = ast.parse(content, filename=str(path))
            cases = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and n.name.startswith('test_') for n in ast.walk(tree))
        except SyntaxError:
            cases = 0
    else:
        cases = len(TEST_CALL.findall(content))
    return loc, cases, len(MARKER.findall(content))

def inventory(root: Path) -> dict:
    root = root.resolve(strict=True)
    files = []
    m = dict(source_files=0, source_loc=0, test_files=0, test_loc=0,
             test_cases=0, docs=0, config_files=0, integration_patches=0,
             maintenance_markers=0)
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.is_symlink() or any(
                part in SKIP for part in path.relative_to(root).parts):
            continue
        rel = path.relative_to(root).as_posix()
        ext = path.suffix.lower()
        if ext == '.patch':
            m['integration_patches'] += 1
        elif ext in DOC:
            m['docs'] += 1
        elif ext in CONFIG and ext not in CODE:
            m['config_files'] += 1
        elif ext in CODE:
            loc, cases, markers = _counts(path)
            kind = 'test' if (rel.startswith('tests/') or '/__tests__/' in '/' + rel
                              or path.stem.startswith('test_') or path.stem.endswith('.test')) else 'source'
            m[kind + '_files'] += 1
            m[kind + '_loc'] += loc
            m['maintenance_markers'] += markers
            if kind == 'test':
                m['test_cases'] += cases
            files.append({'path': rel, 'loc': loc, 'kind': kind})
    top = sorted((f for f in files if f['kind'] == 'source'),
                 key=lambda f: (-f['loc'], f['path']))[:8]
    return dict(schema=1, generated_at=datetime.now(timezone.utc).isoformat(),
                metrics=m, largest_source_files=top)

def assess(current: dict, previous: dict | None = None) -> dict:
    m = current['metrics']
    old = previous.get('metrics', {}) if previous and previous.get('schema') == 1 else {}
    delta = {k: m[k] - old[k] for k in m if isinstance(old.get(k), int)}
    proposals = []
    def add(key, priority, evidence, change):
        proposals.append(dict(id=key, priority=priority, evidence=evidence,
                              proposed_change=change, automatic_execution=False))
    large = [f for f in current['largest_source_files'] if f['loc'] >= 500]
    if large:
        add('split-large-modules', 'medium',
            ', '.join(f"{f['path']} ({f['loc']} lines)" for f in large[:4]),
            'Prepare a reviewed refactor PR with regression tests.')
    if m['integration_patches']:
        add('reconcile-integration-patches', 'high',
            f"{m['integration_patches']} integration patches remain in source",
            'Compare each patch to its deployed counterpart and record independent verification.')
    if m['source_files'] and not m['test_cases']:
        add('add-tests', 'high', 'Source exists but no discoverable test cases',
            'Add deterministic tests for a critical workflow.')
    if m['maintenance_markers'] >= 10:
        add('triage-markers', 'low', f"{m['maintenance_markers']} maintenance markers",
            'Review TODO/FIXME/HACK comments and create actionable issues.')
    if old:
        growth = delta.get('source_loc', 0)
        if old.get('source_loc', 0) > 0 and growth > .2 * old['source_loc'] and delta.get('test_cases', 0) <= 0:
            add('test-growth-mismatch', 'high',
                f"Source grew by {growth} nonblank lines without detected test growth",
                'Test the new functionality before expanding more capabilities.')
        if delta.get('test_cases', 0) < 0:
            add('test-regression', 'high',
                f"Detected test cases fell by {-delta['test_cases']}",
                'Investigate removed or renamed tests and run the full suite.')
    return {**current, 'deltas': delta, 'baseline_available': bool(old),
            'suggestions': proposals,
            'policy': 'Measurements and proposals only. No execution or deployment authority.'}

def markdown(report: dict) -> str:
    lines = ['# Kiki system complexity report', '',
             f"Generated: {report['generated_at']}", '',
             'Repository heuristics only; no live services, personal data, or deployments checked.', '',
             '| Metric | Count | Change |', '|---|---:|---:|']
    for key, value in report['metrics'].items():
        diff = report['deltas'].get(key)
        change = 'n/a' if diff is None else f"{diff:+d}"
        lines.append(f"| {key.replace('_', ' ')} | {value} | {change} |")
    lines.extend(['', '## Proposed improvements', ''])
    if not report['suggestions']:
        lines.append('No heuristic proposals; this does not prove absence of bugs.')
    for p in report['suggestions']:
        lines.extend([f"### {p['id']} ({p['priority']})", '', p['evidence'],
                      '', p['proposed_change'], ''])
    lines.extend(['## Largest source files', ''])
    for f in report['largest_source_files']:
        lines.append(f"- {f['path']}: {f['loc']} nonblank lines")
    lines.extend(['', 'Counts are not coverage measurements. All code changes require review, tests,',
                  'and deployment verification when applicable.', ''])
    return '\n'.join(lines)

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--baseline', type=Path)
    p.add_argument('--json-out', type=Path, required=True)
    p.add_argument('--markdown-out', type=Path, required=True)
    args = p.parse_args(argv)
    previous = None
    if args.baseline and args.baseline.is_file():
        previous = json.loads(args.baseline.read_text(encoding='utf-8'))
    report = assess(inventory(args.root), previous)
    for dest, data in ((args.json_out, json.dumps(report, indent=2) + '\n'),
                       (args.markdown_out, markdown(report))):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(data, encoding='utf-8')
    print(f"Source files: {report['metrics']['source_files']}; "
          f"suggestions: {len(report['suggestions'])}; "
          f"baseline: {report['baseline_available']}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
