#!/usr/bin/env python3
"""RG-08 banned-terms linter (PRD 13.7, 15.4). Stdlib only, Python 3.12+.

Usage:
    python tools/banned_terms.py              # scan the globs in tools/banned_terms.toml
    python tools/banned_terms.py PATH [...]   # scan specific files or directories

Exit status 1 when any banned term is found. A line can be exempted only with an explicit,
reviewed reason on the same line:  `banned-terms-allow: <reason>`.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = Path(__file__).resolve().parent / "banned_terms.toml"
ALLOW_PRAGMA = re.compile(r"banned-terms-allow:\s*\S")
# Whole-word boundaries that also work for accented letters and apostrophes.
_WORD_START = r"(?<![\w’'])"  # noqa: RUF001 - curly apostrophe on purpose
_WORD_END = r"(?![\w’'])"  # noqa: RUF001


@dataclass(frozen=True)
class Term:
    term: str
    lang: str
    regex: re.Pattern[str]


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    col: int
    term: str
    lang: str
    match: str

    def __str__(self) -> str:
        return (
            f'{self.path}:{self.line}:{self.col}: RG-08 banned term "{self.match}" '
            f"({self.lang}: {self.term})"
        )


@dataclass(frozen=True)
class Config:
    include: list[str]
    exclude: list[str]
    terms: list[Term]


def load_config(path: Path = DEFAULT_CONFIG) -> Config:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    terms = []
    for entry in data["terms"]:
        alternation = "|".join(f"(?:{p})" for p in entry["patterns"])
        regex = re.compile(f"{_WORD_START}(?:{alternation}){_WORD_END}", re.IGNORECASE)
        terms.append(Term(entry["term"], entry["lang"], regex))
    return Config(data["scan"]["include"], data["scan"].get("exclude", []), terms)


def _scan_line(
    text: str, line_no: int, col_offset: int, path: str, terms: list[Term]
) -> list[Finding]:
    found = []
    for term in terms:
        for m in term.regex.finditer(text):
            found.append(
                Finding(path, line_no, col_offset + m.start() + 1, term.term, term.lang, m.group(0))
            )
    return found


def scan_text(text: str, path: str = "<text>", config: Config | None = None) -> list[Finding]:
    """Scan every line of `text` (used for non-Python files)."""
    config = config or load_config()
    findings: list[Finding] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if ALLOW_PRAGMA.search(line):
            continue
        findings.extend(_scan_line(line, i, 0, path, config.terms))
    return findings


def _docstring_nodes(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


def scan_python(source: str, path: str = "<python>", config: Config | None = None) -> list[Finding]:
    """Scan only string literals (incl. f-string parts), skipping docstrings and code."""
    config = config or load_config()
    tree = ast.parse(source)
    lines = source.splitlines()
    skip = _docstring_nodes(tree)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in skip:
            continue
        first = node.lineno
        last = node.end_lineno or first
        if any(ALLOW_PRAGMA.search(lines[n - 1]) for n in range(first, last + 1)):
            continue
        for offset, part in enumerate(node.value.splitlines() or [""]):
            col = node.col_offset if offset == 0 else 0
            findings.extend(_scan_line(part, first + offset, col, path, config.terms))
    return findings


def scan_file(path: Path, config: Config, display_root: Path = REPO_ROOT) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []  # binary or unreadable: not user-facing text
    try:
        shown = str(path.resolve().relative_to(display_root))
    except ValueError:
        shown = str(path)
    if path.suffix == ".py":
        return scan_python(text, shown, config)
    return scan_text(text, shown, config)


def _excluded(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, p) for p in patterns)


def collect_files(config: Config, root: Path = REPO_ROOT) -> list[Path]:
    files: set[Path] = set()
    for pattern in config.include:
        for p in root.glob(pattern):
            if p.is_file():
                rel = p.relative_to(root).as_posix()
                if not _excluded(rel, config.exclude):
                    files.add(p)
    return sorted(files)


def _expand(paths: list[str], config: Config) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out.extend(
                f
                for f in sorted(p.rglob("*"))
                if f.is_file() and not _excluded(f.as_posix(), config.exclude)
            )
        elif p.is_file():
            out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("paths", nargs="*", help="files/dirs to scan (default: config globs)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)

    config = load_config(args.config)
    files = _expand(args.paths, config) if args.paths else collect_files(config)
    findings = [f for path in files for f in scan_file(path, config)]
    for finding in findings:
        print(finding)  # noqa: T201 - CLI output
    if findings:
        print(f"\nRG-08: {len(findings)} banned term(s) in user-facing text.", file=sys.stderr)  # noqa: T201
        return 1
    print(f"RG-08: {len(files)} file(s) scanned, no banned terms.")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
