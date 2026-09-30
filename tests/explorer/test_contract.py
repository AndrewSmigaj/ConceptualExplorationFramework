"""The dataset contract: shape, cross-references, and domain neutrality."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from explorer.__main__ import main
from explorer.contract import ContractError, check, load_dataset

REPO = Path(__file__).resolve().parents[2]


def minimal() -> dict:
    """A small synthetic dataset using every part of the contract. No real idea content."""
    ideas = [
        {
            "id": f"x{n}",
            "text": f"Synthetic idea number {n}.",
            "essence": f"Essence {n}.",
            "author": "gen-a" if n % 2 else "gen-b",
            "parents": [] if n == 0 else ["x0"],
            "run": "r1",
            "facets": {"colour": "red" if n % 2 else "blue"},
            "metrics": {"size": float(n)},
            "texts": {"remark": f"A remark on idea {n}."},
            "per_scorer": {"s1": {"rank": n % 3 + 1, "gap": 0.1 * n}},
            "scorings": {"s1": {"dims": {"q": 0.5, "noise": 0.25}, "ref": f"call-{n}"}},
        }
        for n in range(4)
    ]
    ideas[3]["scorings"]["s1"] = {"dims": None, "note": "failed to parse"}
    return {
        "schema_version": 1,
        "meta": {
            "id": "synthetic",
            "title": "Synthetic",
            "generated_at": "2026-09-26T00:00:00Z",
            "producer": "tests/explorer/test_contract.py",
            "context": [{"id": "problem", "title": "Problem", "text": "A problem statement."}],
            "rubric": {
                "id": "r",
                "text": "Rate it.",
                "dimensions": [
                    {"id": "q", "label": "Quality", "min": 0, "max": 1, "direction": "higher",
                     "headline": True},
                    {"id": "noise", "label": "Noise", "min": 0, "max": 1, "direction": "lower"},
                ],
            },
        },
        "scorers": [
            {"id": "s1", "label": "Scorer one", "kind": "model", "generator": "gen-a"},
            {"id": "h", "label": "Human", "kind": "human"},
        ],
        "generators": [{"id": "gen-a", "label": "A"}, {"id": "gen-b", "label": "B"}],
        "fields": [
            {"id": "colour", "label": "Colour", "kind": "facet",
             "values": [{"id": "red", "label": "Red"}, {"id": "blue", "label": "Blue"}]},
            {"id": "size", "label": "Size", "kind": "metric", "unit": "words"},
            {"id": "remark", "label": "Remark", "kind": "text"},
            {"id": "rank", "label": "Rank", "kind": "facet", "per_scorer": True, "ordered": True,
             "values": [{"id": 1, "label": "One"}, {"id": 2, "label": "Two"},
                        {"id": 3, "label": "Three"}]},
            {"id": "gap", "label": "Gap", "kind": "metric", "per_scorer": True},
        ],
        "ideas": ideas,
        "runs": [{"id": "r1", "label": "Run 1", "status": "done", "author": "gen-a",
                  "counts": {"generated": 4}}],
        "edge_kinds": [{"id": "lineage", "label": "Lineage"},
                       {"id": "dup", "label": "Same point", "duplicate": True}],
        "edges": [{"kind": "lineage", "source": "x0", "target": "x1"},
                  {"kind": "dup", "source": "x2", "target": "x3"}],
        "presets": [
            {"id": "p1", "title": "A scatter", "kind": "scatter",
             "spec": {"panels": ["s1"], "x": [{"per_scorer": "gap"}, {"metric": "size"}],
                      "y": [{"dim": "q"}, {"dim_product": ["q", "noise"], "label": "q x noise"}],
                      "split": "author",
                      "filters": [{"id": "f", "label": "Mid",
                                   "where": {"metric:size": [1, 2], "colour": "red"}}]}},
            {"id": "p2", "title": "A projection", "kind": "projection",
             "spec": {"projections": ["pca2d"], "scorers": ["s1"],
                      "color": {"per_scorer": "rank"},
                      "marks": [{"label": "A's", "where": {"author": "gen-a"},
                                 "symbol": "diamond"}]}},
            {"id": "p3", "title": "A table", "kind": "table",
             "spec": {"rows": {"field": "colour"},
                      "columns": [{"kind": "count", "label": "n"},
                                  {"kind": "per_scorer_counts", "per_scorer": "rank",
                                   "scorers": ["s1"]}]}},
            {"id": "p4", "title": "Paired", "kind": "paired",
             "spec": {"panels": ["s1"], "reference": "h", "x": {"per_scorer": "rank"},
                      "y": [{"dim": "q"}]}},
        ],
        "projections": {
            "pca2d": {"method": "pca", "dims": 2,
                      "coords": {f"x{n}": [float(n), 0.0] for n in range(4)}},
        },
        "clusterings": {
            "c": {"method": "hdbscan", "assignments": {"x0": 0, "x1": 0, "x2": 1, "x3": -1},
                  "clusters": [{"id": 0, "size": 2, "terms": ["a"]}, {"id": 1, "size": 1}]},
        },
    }


def test_minimal_dataset_is_valid():
    assert check(minimal()) == []


def test_missing_required_key_is_a_schema_problem():
    d = minimal()
    del d["ideas"]
    problems = check(d)
    assert problems and all(p.startswith("schema:") for p in problems)


def test_unknown_top_level_key_is_rejected():
    d = minimal()
    d["extra"] = 1
    assert any("extra" in p for p in check(d))


BREAKS = {
    "duplicate idea id": lambda d: d["ideas"].append(copy.deepcopy(d["ideas"][0])),
    "unknown author": lambda d: d["ideas"][0].update(author="nobody"),
    "unknown parent": lambda d: d["ideas"][1].update(parents=["missing"]),
    "unknown run": lambda d: d["ideas"][0].update(run="r9"),
    "undeclared facet": lambda d: d["ideas"][0]["facets"].update(shape="round"),
    "undeclared facet value": lambda d: d["ideas"][0]["facets"].update(colour="green"),
    "metric used as facet": lambda d: d["ideas"][0]["facets"].update(size="big"),
    "non-finite metric": lambda d: d["ideas"][0]["metrics"].update(size=float("nan")),
    "per-scorer field used globally": lambda d: d["ideas"][0]["metrics"].update(gap=1.0),
    "global field used per scorer": lambda d: d["ideas"][0]["per_scorer"]["s1"].update(size=1.0),
    "per_scorer unknown scorer": lambda d: d["ideas"][0]["per_scorer"].update(zz={"gap": 1.0}),
    "scoring by unknown scorer": lambda d: d["ideas"][0]["scorings"].update(
        zz={"dims": {"q": 0.1, "noise": 0.1}}),
    "score out of range": lambda d: d["ideas"][0]["scorings"]["s1"]["dims"].update(q=1.5),
    "missing dimension": lambda d: d["ideas"][0]["scorings"]["s1"]["dims"].pop("noise"),
    "scorer names unknown generator": lambda d: d["scorers"][0].update(generator="nobody"),
    "edge to unknown idea": lambda d: d["edges"].append(
        {"kind": "lineage", "source": "x0", "target": "gone"}),
    "projection misses an idea": lambda d: d["projections"]["pca2d"]["coords"].pop("x3"),
    "projection wrong length": lambda d: d["projections"]["pca2d"]["coords"].update(
        x0=[1.0, 2.0, 3.0]),
    "undeclared edge kind": lambda d: d["edges"].append(
        {"kind": "other", "source": "x0", "target": "x1"}),
    "cluster size mismatch": lambda d: d["clusterings"]["c"]["clusters"][0].update(size=5),
    "two headline dimensions": lambda d: d["meta"]["rubric"]["dimensions"][1].update(
        headline=True),
    "metric declares values": lambda d: d["fields"][1].update(values=[]),
    "text used as metric": lambda d: d["ideas"][0]["metrics"].update(remark=1.0),
    "text value not a string": lambda d: d["ideas"][0]["texts"].update(remark=3),
    "text declares a unit": lambda d: d["fields"][2].update(unit="x"),
    "facet declares a sequence": lambda d: d["fields"][0].update(sequence=True),
    "preset: undeclared field": lambda d: d["presets"][0]["spec"]["x"].append(
        {"metric": "nope"}),
    "preset: facet used as metric": lambda d: d["presets"][0]["spec"]["x"].append(
        {"metric": "colour"}),
    "preset: global field as per-scorer": lambda d: d["presets"][0]["spec"]["x"].append(
        {"per_scorer": "size"}),
    "preset: unknown dimension": lambda d: d["presets"][0]["spec"]["y"].append({"dim": "zz"}),
    "preset: unknown product dimension": lambda d: d["presets"][0]["spec"]["y"].append(
        {"dim_product": ["q", "zz"]}),
    "preset: unknown panel scorer": lambda d: d["presets"][0]["spec"].update(panels=["zz"]),
    "preset: unknown reference scorer": lambda d: d["presets"][3]["spec"].update(reference="zz"),
    "preset: where on undeclared field": lambda d: d["presets"][1]["spec"]["marks"][0].update(
        where={"shape": "x"}),
    "preset: unknown projection": lambda d: d["presets"][1]["spec"].update(
        projections=["umap9d"]),
    "preset: unknown kind": lambda d: d["presets"][0].update(kind="pie"),
}


@pytest.mark.parametrize("name", sorted(BREAKS))
def test_each_break_is_caught(name):
    d = minimal()
    BREAKS[name](d)
    assert check(d), f"{name} was not caught"


def test_load_and_cli(tmp_path, capsys):
    (tmp_path / "dataset.json").write_text(json.dumps(minimal()), encoding="utf-8")
    assert load_dataset(tmp_path)["meta"]["id"] == "synthetic"
    assert main(["validate", str(tmp_path)]) == 0

    bad = minimal()
    bad["ideas"][0]["author"] = "nobody"
    (tmp_path / "dataset.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ContractError):
        load_dataset(tmp_path)
    assert main(["validate", str(tmp_path)]) == 1
    assert "unknown author" in capsys.readouterr().err


# The explorer renders what a dataset declares. It must never name one domain's
# models, arms, judges or rubric dimensions (CLAUDE.md, domain neutrality).
FORBIDDEN = re.compile(
    r"opus|sonnet|claude|critique|tier|seeded|oceanograph|ringing|"
    r"centrality|dead_weight|single_issue|asked.again",
    re.IGNORECASE,
)
SCANNED = ("*.py", "*.json", "*.ts", "*.svelte", "*.css", "*.html")


def explorer_sources() -> list[Path]:
    root = REPO / "explorer"
    files = [p for pattern in SCANNED for p in root.rglob(pattern)]
    skip = {"node_modules", "dist"}
    return [p for p in files if not skip & set(p.relative_to(root).parts)
            and p.name not in {"package.json", "package-lock.json"}]


def test_explorer_code_is_domain_neutral():
    files = explorer_sources()
    assert files, "no explorer sources found"
    leaks = [f"{p.relative_to(REPO)}:{n}: {line.strip()}"
             for p in files
             for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
             if FORBIDDEN.search(line)]
    assert not leaks, "domain names in explorer code:\n" + "\n".join(leaks)


def test_subset_stays_valid_and_drops_references():
    from explorer.contract import subset

    d = minimal()
    kept = subset(d, {"x1", "x2", "x3"})             # x0 is every other idea's parent
    assert check(kept) == []
    assert [i["id"] for i in kept["ideas"]] == ["x1", "x2", "x3"]
    assert all(i["parents"] == [] for i in kept["ideas"])
    assert [e["kind"] for e in kept["edges"]] == ["dup"]     # x0's lineage edge is gone
    assert set(kept["projections"]["pca2d"]["coords"]) == {"x1", "x2", "x3"}
    sizes = {c["id"]: c["size"] for c in kept["clusterings"]["c"]["clusters"]}
    assert sizes == {0: 1, 1: 1}
    assert check(subset(d, {"x3"})) == []           # every real cluster emptied
    assert len(d["ideas"]) == 4                      # the original is untouched
