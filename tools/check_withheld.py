#!/usr/bin/env python3
"""Stop withheld material from entering this public repository.

An earlier pilot used example problems that must not be published. They, and every
text generated from them, live in a private archive outside this repository. This
check reads two things from that archive:

  - withheld-patterns.txt: case-insensitive regular expressions, one per line;
  - the withheld texts themselves, compared by runs of eight consecutive words, so
    a lightly reworded passage is still caught.

The patterns are kept in the archive, not here, because the words themselves would
reveal what is withheld.

Usage:
  python tools/check_withheld.py --staged   check the files staged for commit (the pre-commit hook)
  python tools/check_withheld.py --all      check every tracked file

The archive is found at $WITHHELD_ARCHIVE, or ~/critique-pilot-archive by default.
The hook is enabled per clone with: git config core.hooksPath tools/hooks
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = Path.home() / "critique-pilot-archive"
WITHHELD_TEXT_PATTERNS = ["projects/*/sources/*", "experiments/*/data/ideas.jsonl",
                          "experiments/*/data/seeds.json"]
WORDS_PER_RUN = 8
MINIMUM_WITHHELD_RUNS = 1000
BINARY_SUFFIXES = (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".npy", ".pkl",
                   ".parquet", ".woff", ".woff2")


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def word_runs(text: str) -> set[tuple[str, ...]]:
    found = words(text)
    return {tuple(found[i:i + WORDS_PER_RUN]) for i in range(len(found) - WORDS_PER_RUN + 1)}


def load_archive(archive: Path) -> tuple[list[re.Pattern[str]], set[tuple[str, ...]]]:
    pattern_file = archive / "withheld-patterns.txt"
    if not pattern_file.exists():
        sys.exit(f"check_withheld: no pattern file at {pattern_file}. Set WITHHELD_ARCHIVE "
                 "to the private archive's folder.")
    patterns = [re.compile(line.strip(), re.IGNORECASE)
                for line in pattern_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")]
    runs: set[tuple[str, ...]] = set()
    for glob in WITHHELD_TEXT_PATTERNS:
        for path in archive.glob(glob):
            runs |= word_runs(path.read_text(encoding="utf-8", errors="replace"))
    if len(runs) < MINIMUM_WITHHELD_RUNS:
        sys.exit(f"check_withheld: only {len(runs)} withheld word runs found in {archive}; "
                 "the overlap check would be meaningless.")
    return patterns, runs


def git(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=REPOSITORY, capture_output=True,
                          text=True, check=True).stdout


def files_to_check(staged: bool) -> dict[str, str]:
    """Path -> text: the staged version of each staged file, or every tracked file."""
    if staged:
        paths = git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines()
    else:
        paths = git("ls-files").splitlines()
    texts = {}
    for path in paths:
        if path.lower().endswith(BINARY_SUFFIXES):
            continue
        if staged:
            text = git("show", f":{path}")
        else:
            text = (REPOSITORY / path).read_text(encoding="utf-8", errors="replace")
        if "\x00" not in text:
            texts[path] = text
    return texts


def problems_in(path: str, text: str, patterns: list[re.Pattern[str]],
                runs: set[tuple[str, ...]]) -> list[str]:
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        for pattern in patterns:
            if pattern.search(line):
                found.append(f"{path}:{number}: matches a withheld pattern ({pattern.pattern})")
    shared = word_runs(text) & runs
    if shared:
        found.append(f"{path}: shares {len(shared)} eight-word runs with withheld text")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--staged", action="store_true")
    which.add_argument("--all", action="store_true")
    arguments = parser.parse_args()

    archive = Path(os.environ.get("WITHHELD_ARCHIVE", DEFAULT_ARCHIVE)).expanduser()
    patterns, runs = load_archive(archive)
    problems = []
    for path, text in files_to_check(arguments.staged).items():
        problems += problems_in(path, text, patterns, runs)
    if problems:
        print("Withheld material found; nothing was committed:", *problems, sep="\n  ",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
