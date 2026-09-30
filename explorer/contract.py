"""The dataset contract: load a dataset directory and check it.

A dataset directory holds:
  dataset.json      read-only to the app; validated here
  embeddings.npy    optional: one row per idea, float32, rows in the order of
  embeddings.json   its sidecar's `ids`; used by `enrich` so projections share
                    the producer's vector space
  annotations/      written only by the server (ratings, notes)

The JSON Schema checks shape; the checks here cover what a schema cannot:
unique ids, references that resolve, facet values that were declared, and
scores inside their rubric's range.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "dataset.schema.json"
DATASET_FILE = "dataset.json"
EMBEDDINGS_FILE, EMBEDDINGS_META = "embeddings.npy", "embeddings.json"
ANNOTATIONS_DIR = "annotations"


class ContractError(Exception):
    """The dataset does not satisfy the contract. `problems` lists every violation."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__(f"{len(problems)} contract problem(s):\n" + "\n".join(problems))


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_dataset(directory: Path) -> dict:
    """Read and validate `dataset.json`. Raises ContractError on any problem."""
    data = json.loads((directory / DATASET_FILE).read_text(encoding="utf-8"))
    problems = check(data)
    if problems:
        raise ContractError(problems)
    return data


def load_embeddings(directory: Path, idea_ids: list[str]):
    """The dataset's embeddings, one row per idea in `idea_ids` order, or None if absent.

    Raises ContractError if the sidecar does not cover exactly the dataset's ideas.
    """
    import numpy as np

    path, meta_path = directory / EMBEDDINGS_FILE, directory / EMBEDDINGS_META
    if not path.exists():
        return None, None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    vectors = np.load(path)
    ids = meta.get("ids", [])
    problems = []
    if len(ids) != vectors.shape[0]:
        problems.append(f"embeddings: {vectors.shape[0]} rows but {len(ids)} ids in the sidecar")
    if set(ids) != set(idea_ids) or len(ids) != len(set(ids)):
        problems.append(f"embeddings: ids do not match the dataset's {len(idea_ids)} ideas")
    if problems:
        raise ContractError(problems)
    row = {i: n for n, i in enumerate(ids)}
    return vectors[[row[i] for i in idea_ids]], meta


def check(data: Any) -> list[str]:
    """Every contract violation in `data`, or an empty list."""
    validator = Draft202012Validator(load_schema())
    problems = [
        f"schema: {'/'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    ]
    if problems:
        # Cross-reference checks assume the shape is right.
        return problems
    return _check_references(data)


def _duplicates(ids: list) -> list:
    seen, dup = set(), []
    for i in ids:
        if i in seen and i not in dup:
            dup.append(i)
        seen.add(i)
    return dup


def _finite(value: Any) -> bool:
    return not isinstance(value, float) or math.isfinite(value)


def _check_references(data: dict) -> list[str]:
    out: list[str] = []

    def unique(kind: str, items: list[dict]) -> set:
        ids = [x["id"] for x in items]
        for d in _duplicates(ids):
            out.append(f"{kind}: duplicate id {d!r}")
        return set(ids)

    generators = unique("generators", data["generators"])
    scorers = unique("scorers", data["scorers"])
    fields = {f["id"]: f for f in data["fields"]}
    unique("fields", data["fields"])
    ideas = unique("ideas", data["ideas"])
    runs = unique("runs", data.get("runs", []))
    unique("presets", data.get("presets", []))

    rubric = data["meta"].get("rubric")
    dims = {d["id"]: d for d in rubric["dimensions"]} if rubric else {}
    if rubric:
        unique("rubric dimensions", rubric["dimensions"])
        for d in rubric["dimensions"]:
            if d["min"] >= d["max"]:
                out.append(f"rubric: dimension {d['id']!r} has min >= max")
        if sum(1 for d in rubric["dimensions"] if d.get("headline")) > 1:
            out.append("rubric: more than one headline dimension")

    for s in data["scorers"]:
        if "generator" in s and s["generator"] not in generators:
            out.append(f"scorers: {s['id']!r} names unknown generator {s['generator']!r}")

    for f in data["fields"]:
        if f["kind"] != "facet" and ("values" in f or "ordered" in f):
            out.append(f"fields: {f['kind']} {f['id']!r} declares facet-only keys")
        if f["kind"] != "metric" and ("unit" in f or "sequence" in f):
            out.append(f"fields: {f['kind']} {f['id']!r} declares metric-only keys")
        if "values" in f:
            for d in _duplicates([v["id"] for v in f["values"]]):
                out.append(f"fields: {f['id']!r} has duplicate value {d!r}")

    def check_value(where: str, field_id: str, value: Any, per_scorer: bool) -> None:
        f = fields.get(field_id)
        if f is None:
            out.append(f"{where}: undeclared field {field_id!r}")
            return
        if bool(f.get("per_scorer", False)) != per_scorer:
            scope = "per scorer" if f.get("per_scorer") else "not per scorer"
            out.append(f"{where}: field {field_id!r} is declared {scope}")
            return
        if value is None:
            return
        if f["kind"] == "text":
            if not isinstance(value, str):
                out.append(f"{where}: text {field_id!r} is not a string")
        elif f["kind"] == "metric":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                out.append(f"{where}: metric {field_id!r} is not a number")
            elif not _finite(value):
                out.append(f"{where}: metric {field_id!r} is not finite")
        elif "values" in f and value not in {v["id"] for v in f["values"]}:
            out.append(f"{where}: facet {field_id!r} has undeclared value {value!r}")

    for idea in data["ideas"]:
        where = f"idea {idea['id']}"
        if "author" in idea and idea["author"] not in generators:
            out.append(f"{where}: unknown author {idea['author']!r}")
        for p in idea.get("parents", []):
            if p not in ideas:
                out.append(f"{where}: unknown parent {p!r}")
        if "run" in idea and idea["run"] not in runs:
            out.append(f"{where}: unknown run {idea['run']!r}")
        for bucket, kind in (("facets", "facet"), ("metrics", "metric"), ("texts", "text")):
            for k, v in idea.get(bucket, {}).items():
                declared = fields.get(k, {}).get("kind")
                if declared and declared != kind:
                    out.append(f"{where}: {k!r} is a {declared}, not a {kind}")
                else:
                    check_value(where, k, v, per_scorer=False)
        for scorer, values in idea.get("per_scorer", {}).items():
            if scorer not in scorers:
                out.append(f"{where}: per_scorer names unknown scorer {scorer!r}")
            for k, v in values.items():
                check_value(f"{where} [{scorer}]", k, v, per_scorer=True)
        for scorer, scoring in idea.get("scorings", {}).items():
            if scorer not in scorers:
                out.append(f"{where}: scoring by unknown scorer {scorer!r}")
            got = scoring["dims"]
            if got is None:
                continue
            if not rubric:
                out.append(f"{where}: has scorings but the dataset declares no rubric")
                continue
            if set(got) != set(dims):
                missing, extra = set(dims) - set(got), set(got) - set(dims)
                out.append(f"{where} [{scorer}]: dimensions differ from the rubric "
                           f"(missing {sorted(missing)}, extra {sorted(extra)})")
            for k, v in got.items():
                d = dims.get(k)
                if d and not (_finite(v) and d["min"] <= v <= d["max"]):
                    out.append(f"{where} [{scorer}]: {k}={v} outside [{d['min']}, {d['max']}]")

    for r in data.get("runs", []):
        if "author" in r and r["author"] not in generators:
            out.append(f"run {r['id']}: unknown author {r['author']!r}")

    edge_kinds = unique("edge_kinds", data.get("edge_kinds", []))
    for n, e in enumerate(data.get("edges", [])):
        for end in ("source", "target"):
            if e[end] not in ideas:
                out.append(f"edge {n}: unknown {end} {e[end]!r}")
        if e["kind"] not in edge_kinds:
            out.append(f"edge {n}: undeclared kind {e['kind']!r}")

    for pid, proj in data.get("projections", {}).items():
        coords = proj["coords"]
        if set(coords) != ideas:
            out.append(f"projection {pid}: covers {len(set(coords) & ideas)} of {len(ideas)} "
                       f"ideas, with {len(set(coords) - ideas)} unknown ids")
        bad = [i for i, c in coords.items() if len(c) != proj["dims"] or not all(map(_finite, c))]
        if bad:
            out.append(f"projection {pid}: {len(bad)} coordinates of the wrong length or not finite")

    for cid, cl in data.get("clusterings", {}).items():
        assigned = cl["assignments"]
        if set(assigned) != ideas:
            out.append(f"clustering {cid}: assigns {len(set(assigned) & ideas)} of {len(ideas)} ideas")
        declared = {c["id"]: c["size"] for c in cl["clusters"]}
        counts: dict[int, int] = {}
        for k in assigned.values():
            counts[k] = counts.get(k, 0) + 1
        for k, n in counts.items():
            if k != -1 and declared.get(k) != n:
                out.append(f"clustering {cid}: cluster {k} has {n} members, declares {declared.get(k)}")
        for k in declared:
            if k not in counts:
                out.append(f"clustering {cid}: cluster {k} is declared but empty")

    for preset in data.get("presets", []):
        out += _check_preset(preset, fields, scorers, set(dims), data.get("projections"))

    return out


REF_KEYS = ("metric", "per_scorer", "dim", "dim_product", "field")


def _check_preset(preset: dict, fields: dict, scorers: set, dims: set,
                  projections: dict | None) -> list[str]:
    """Every field, dimension, scorer and projection a preset names must exist, with the
    right kind. The grammar itself is documented in explorer/README.md."""
    where = f"preset {preset['id']}"
    out: list[str] = []

    def field_ok(field_id: str, kind: str | None, per_scorer: bool, context: str) -> None:
        f = fields.get(field_id)
        if f is None:
            out.append(f"{where}: {context} names undeclared field {field_id!r}")
        elif kind and f["kind"] != kind:
            out.append(f"{where}: {context} needs a {kind}, {field_id!r} is a {f['kind']}")
        elif bool(f.get("per_scorer")) != per_scorer:
            out.append(f"{where}: {context} {field_id!r} per-scorer mismatch")

    def ref(r: dict, context: str) -> None:
        if "metric" in r:
            field_ok(r["metric"], "metric", False, context)
        elif "field" in r:
            field_ok(r["field"], "facet", False, context)
        elif "per_scorer" in r:
            field_ok(r["per_scorer"], None, True, context)
        elif "dim" in r:
            if r["dim"] not in dims:
                out.append(f"{where}: {context} names unknown dimension {r['dim']!r}")
        elif "dim_product" in r:
            for d in r["dim_product"]:
                if d not in dims:
                    out.append(f"{where}: {context} names unknown dimension {d!r}")

    def condition(w: dict, context: str) -> None:
        for key in w:
            if key == "author":
                continue
            if key.startswith("metric:"):
                field_ok(key.removeprefix("metric:"), "metric", False, context)
            else:
                field_ok(key, "facet", False, context)

    def scorer_list(ids, context: str) -> None:
        for s in [ids] if isinstance(ids, str) else ids:
            if s not in scorers:
                out.append(f"{where}: {context} names unknown scorer {s!r}")

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            if any(k in node for k in REF_KEYS):
                ref(node, path)
            for k, v in node.items():
                if k == "where" and isinstance(v, dict):
                    condition(v, f"{path}.where")
                elif k in ("panels", "scorers", "reference"):
                    scorer_list(v, f"{path}.{k}")
                elif k == "projections" and projections is not None:
                    for pid in v:
                        if pid not in projections:
                            out.append(f"{where}: unknown projection {pid!r}")
                elif k not in REF_KEYS:
                    walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for n, v in enumerate(node):
                walk(v, f"{path}[{n}]")

    walk(preset["spec"], "spec")
    return out


def subset(data: dict, keep: set[str]) -> dict:
    """The dataset restricted to the ideas in `keep`, still satisfying the contract.

    Edges, projections and clusterings lose the ideas left out; cluster sizes are
    recounted and emptied clusters dropped. A kept idea whose parent is left out
    keeps no dangling reference: that parent pointer is removed.
    """
    import copy

    out = copy.deepcopy(data)
    out["ideas"] = [i for i in out["ideas"] if i["id"] in keep]
    for idea in out["ideas"]:
        if "parents" in idea:
            idea["parents"] = [p for p in idea["parents"] if p in keep]
    if "edges" in out:
        out["edges"] = [e for e in out["edges"] if e["source"] in keep and e["target"] in keep]
    for proj in out.get("projections", {}).values():
        proj["coords"] = {i: c for i, c in proj["coords"].items() if i in keep}
    for cl in out.get("clusterings", {}).values():
        cl["assignments"] = {i: k for i, k in cl["assignments"].items() if i in keep}
        sizes: dict[int, int] = {}
        for k in cl["assignments"].values():
            sizes[k] = sizes.get(k, 0) + 1
        cl["clusters"] = [{**c, "size": sizes[c["id"]]} for c in cl["clusters"]
                          if sizes.get(c["id"])]
    return out
