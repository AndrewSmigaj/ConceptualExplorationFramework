"""The pre-commit check that keeps withheld material out of this public repository.

A fake archive is built here, with made-up patterns and texts, so the test never
needs the real private archive.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import check_withheld


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    (tmp_path / "withheld-patterns.txt").write_text(
        "# made-up patterns for the test\nzorblax\n\\bquint\\b\n", encoding="utf-8")
    rng = random.Random(0)
    vocabulary = [f"word{n}" for n in range(500)]
    text = " ".join(rng.choice(vocabulary) for _ in range(3000))
    source = tmp_path / "projects" / "secret" / "sources"
    source.mkdir(parents=True)
    (source / "argument.txt").write_text(text, encoding="utf-8")
    return tmp_path


def test_clean_text_passes(archive: Path) -> None:
    patterns, runs = check_withheld.load_archive(archive)
    assert check_withheld.problems_in("README.md", "A plain public sentence.", patterns, runs) == []


def test_a_withheld_pattern_is_caught_case_insensitively(archive: Path) -> None:
    patterns, runs = check_withheld.load_archive(archive)
    problems = check_withheld.problems_in("doc.md", "line one\nThe ZORBLAX case\n", patterns, runs)
    assert problems == ["doc.md:2: matches a withheld pattern (zorblax)"]


def test_word_boundaries_in_patterns_are_respected(archive: Path) -> None:
    patterns, runs = check_withheld.load_archive(archive)
    assert check_withheld.problems_in("a.md", "quintessential", patterns, runs) == []
    assert check_withheld.problems_in("a.md", "a quint here", patterns, runs) != []


def test_eight_shared_words_are_caught_even_when_reworded_around(archive: Path) -> None:
    patterns, runs = check_withheld.load_archive(archive)
    secret = (archive / "projects/secret/sources/argument.txt").read_text().split()
    leaked = "Some new framing. " + " ".join(secret[100:108]) + " and more of our own words."
    problems = check_withheld.problems_in("notes.md", leaked, patterns, runs)
    assert problems and "eight-word runs" in problems[0]


def test_seven_shared_words_are_not_enough(archive: Path) -> None:
    patterns, runs = check_withheld.load_archive(archive)
    secret = (archive / "projects/secret/sources/argument.txt").read_text().split()
    near = "start " + " ".join(secret[100:107]) + " end"
    assert check_withheld.problems_in("notes.md", near, patterns, runs) == []


def test_a_missing_archive_stops_the_commit(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="no pattern file"):
        check_withheld.load_archive(tmp_path / "nowhere")


def test_too_little_withheld_text_stops_the_commit(tmp_path: Path) -> None:
    (tmp_path / "withheld-patterns.txt").write_text("zorblax\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="meaningless"):
        check_withheld.load_archive(tmp_path)
