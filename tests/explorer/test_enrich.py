"""enrich: an anchored layout, fixed seeds, planted clusters found, and valid output."""

from __future__ import annotations

import json

import numpy as np
import pytest

from explorer.contract import ContractError, check
from explorer.enrich import LAYOUT_DIR, PARAMS, enrich, pca

TOPICS = ["glacier ice meltwater", "violin bow rosin", "orbit comet perihelion"]
PARAMS_SMALL = {**PARAMS, "hdbscan": {"min_cluster_size": 5, "min_samples": 3},
                "terms_max_df": 0.5}


def planted(n_per: int = 25, dim: int = 24, seed: int = 0, topics=TOPICS, prefix="t"):
    """Well-separated blobs, each with its own vocabulary. Synthetic, no real content."""
    rng = np.random.default_rng(seed)
    centres = np.random.default_rng(99).normal(size=(len(TOPICS) + 1, dim)) * 4
    vectors, ideas, truth = [], [], []
    for t, topic in enumerate(topics):
        for n in range(n_per):
            v = centres[TOPICS.index(topic) if topic in TOPICS else -1] + rng.normal(size=dim)
            vectors.append(v / np.linalg.norm(v))
            ideas.append({"id": f"{prefix}{t}n{n}", "text": f"Idea {n} about {topic}.",
                          "essence": f"A point concerning {topic}, variant {n}."})
            truth.append(t)
    return ideas, np.asarray(vectors, dtype=np.float32), truth


def write(directory, ideas, vectors):
    dataset = {
        "schema_version": 1,
        "meta": {"id": "planted", "title": "Planted", "generated_at": "2026-09-26T00:00:00Z",
                 "producer": "tests/explorer/test_enrich.py"},
        "scorers": [], "generators": [], "fields": [], "ideas": ideas,
    }
    (directory / "dataset.json").write_text(json.dumps(dataset), encoding="utf-8")
    np.save(directory / "embeddings.npy", vectors)
    (directory / "embeddings.json").write_text(
        json.dumps({"ids": [i["id"] for i in ideas]}), encoding="utf-8")


@pytest.fixture
def dataset_dir(tmp_path):
    ideas, vectors, truth = planted()
    write(tmp_path, ideas, vectors)
    return tmp_path, truth


def test_first_run_fits_and_saves_a_layout(dataset_dir):
    directory, _ = dataset_dir
    data, status = enrich(directory, PARAMS_SMALL)
    assert check(data) == []
    assert "fitted a new layout on 75 ideas" in status
    assert set(data["projections"]) == {"umap3d", "umap2d", "pca3d", "pca2d"}
    assert (directory / LAYOUT_DIR / "anchor.pkl").exists()
    on_disk = json.loads((directory / "dataset.json").read_text(encoding="utf-8"))
    assert on_disk["projections"] == data["projections"]


def test_rerun_keeps_the_layout_exactly(dataset_dir):
    directory, _ = dataset_dir
    first, _ = enrich(directory, PARAMS_SMALL)
    again, status = enrich(directory, PARAMS_SMALL)
    assert "kept the layout" in status
    assert again["projections"] == first["projections"]
    assert again["clusterings"] == first["clusterings"]


def test_new_ideas_are_placed_without_moving_the_old(dataset_dir):
    directory, _ = dataset_dir
    first, _ = enrich(directory, PARAMS_SMALL)
    ideas, vectors, _ = planted()
    # A new batch of the first topic: it should land among that topic's anchored ideas.
    new_ideas, new_vectors, _ = planted(n_per=8, seed=7, topics=[TOPICS[0]], prefix="new")
    write(directory, ideas + new_ideas, np.vstack([vectors, new_vectors]))
    second, status = enrich(directory, PARAMS_SMALL)
    assert "placed 8 new ideas" in status and check(second) == []
    for pid in ("umap3d", "umap2d", "pca3d", "pca2d"):
        old, new = first["projections"][pid]["coords"], second["projections"][pid]["coords"]
        assert all(new[i] == old[i] for i in old), f"{pid}: an anchored idea moved"
    assert second["projections"]["umap3d"]["params"]["placed"] == 8
    # Placed near their own topic, and joined its cluster.
    coords = second["projections"]["umap3d"]["coords"]
    def centre(ids):
        return np.mean([coords[i] for i in ids], axis=0)

    topic0 = centre([i["id"] for i in ideas if i["id"].startswith("t0")])
    others = [centre([i["id"] for i in ideas if i["id"].startswith(f"t{t}")]) for t in (1, 2)]
    for i in new_ideas:
        p = np.array(coords[i["id"]])
        assert np.linalg.norm(p - topic0) < min(np.linalg.norm(p - o) for o in others)
    labels = second["clusterings"]["hdbscan"]["assignments"]
    home = {labels[i["id"]] for i in ideas if i["id"].startswith("t0")} - {-1}
    assert all(labels[i["id"]] in home for i in new_ideas)


def test_layout_is_refitted_when_it_cannot_be_reused(dataset_dir):
    directory, _ = dataset_dir
    enrich(directory, PARAMS_SMALL)
    ideas, vectors, _ = planted()
    write(directory, ideas[1:], vectors[1:])                     # an anchored idea is gone
    _, status = enrich(directory, PARAMS_SMALL)
    assert "no longer in the dataset" in status
    _, status = enrich(directory, {**PARAMS_SMALL, "terms": 3})  # parameters changed
    assert "parameters changed" in status
    _, status = enrich(directory, {**PARAMS_SMALL, "terms": 3}, refit=True)
    assert "asked to refit" in status


def test_planted_clusters_are_found_and_labelled(dataset_dir):
    directory, truth = dataset_dir
    data, _ = enrich(directory, PARAMS_SMALL)
    cl = data["clusterings"]["hdbscan"]
    ids = [f"t{t}n{n}" for t in range(len(TOPICS)) for n in range(25)]
    found = [cl["assignments"][i] for i in ids]
    # Each planted blob lands in one cluster, and different blobs in different ones.
    by_blob = [{k for k, t in zip(found, truth) if t == b} - {-1} for b in range(len(TOPICS))]
    assert all(len(s) == 1 for s in by_blob)
    assert len(set().union(*by_blob)) == len(TOPICS)
    # Each cluster's label names its blob's vocabulary, not the shared template.
    for blob, topic in enumerate(TOPICS):
        (k,) = by_blob[blob]
        terms = next(c["terms"] for c in cl["clusters"] if c["id"] == k)
        assert set(" ".join(terms).split()) & set(topic.split())
        assert not {"point", "concerning", "variant"} & set(" ".join(terms).split())
    sizes = [c["size"] for c in cl["clusters"]]
    assert sizes == sorted(sizes, reverse=True)


def test_pca_signs_are_fixed():
    rng = np.random.default_rng(1)
    x = rng.normal(size=(40, 6))
    a, var = pca(x, 3)
    b, _ = pca(x * 1.0, 3)
    assert np.allclose(a, b)
    assert var == sorted(var, reverse=True) and 0 < sum(var) <= 1


def test_enrich_refuses_without_embeddings(dataset_dir):
    directory, _ = dataset_dir
    (directory / "embeddings.npy").unlink()
    with pytest.raises(ContractError):
        enrich(directory, PARAMS_SMALL)


def test_enrich_refuses_mismatched_embeddings(dataset_dir):
    directory, _ = dataset_dir
    meta = json.loads((directory / "embeddings.json").read_text(encoding="utf-8"))
    meta["ids"][0] = "somebody-else"
    (directory / "embeddings.json").write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ContractError):
        enrich(directory, PARAMS_SMALL)
