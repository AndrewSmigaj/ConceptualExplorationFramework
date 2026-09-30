"""Projections and clusterings for a dataset: `python -m explorer enrich <dataset-dir>`.

Computed in Python with fixed seeds, never in the browser, so every view shows the
same geometry.

  pca3d, pca2d    linear, with explained variance: the honest check on UMAP
  umap3d, umap2d  the default views (brief section 13); UMAP can make structure
                  look cleaner than it is, so PCA is always one toggle away
  clusterings     HDBSCAN on a 10-dimensional UMAP of the embeddings, labelled
                  with the top class-based TF-IDF terms of each cluster's
                  essences. No model calls.

The layout is anchored. The first run fits every projection and saves the fitted
models in <dataset>/.layout/ (git-ignored). Later runs leave the anchored ideas
exactly where they were and place any new ideas into the same space with the
saved models, so a new arm lands among the old ones instead of redrawing the
map. New ideas join a cluster when most of their nearest anchored neighbours
share one. `--refit` fits everything afresh and re-anchors.

The anchor is refitted automatically, with a message, if an anchored idea has
gone, its embedding changed, or the parameters changed.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import pickle
from pathlib import Path

import numpy as np

from explorer.contract import DATASET_FILE, ContractError, check, load_dataset, load_embeddings

LAYOUT_DIR = ".layout"
PARAMS: dict = {
    "seed": 42,
    "umap": {"n_neighbors": 15, "min_dist": 0.1, "metric": "cosine"},
    "cluster_umap": {"n_components": 10, "n_neighbors": 15, "min_dist": 0.0, "metric": "cosine"},
    "hdbscan": {"min_cluster_size": 12, "min_samples": 5},
    "terms": 4,
    # Terms in more than this share of all texts are boilerplate (a fixed essence
    # form, the problem's own vocabulary) and never label a cluster.
    "terms_max_df": 0.25,
    # A newly placed idea joins a cluster when at least `agree` of its `k` nearest
    # anchored neighbours (in the clustering space) belong to it.
    "place": {"k": 5, "agree": 3},
}


def pca_fit(vectors: np.ndarray, dims: int) -> tuple[np.ndarray, np.ndarray, list[float]]:
    """Mean, the first `dims` components, and each component's share of variance.

    Signs are fixed so each component's largest loading is positive; SVD alone
    leaves them arbitrary, which would flip the picture between runs.
    """
    mean = vectors.mean(axis=0)
    _, s, vt = np.linalg.svd(vectors - mean, full_matrices=False)
    vt = vt[:dims]
    signs = np.sign(vt[np.arange(dims), np.abs(vt).argmax(axis=1)])
    variance = (s**2) / (s**2).sum()
    return mean, vt * signs[:, None], [round(float(v), 4) for v in variance[:dims]]


def pca(vectors: np.ndarray, dims: int = 3) -> tuple[np.ndarray, list[float]]:
    """Coordinates on the first `dims` components, and their shares of variance."""
    mean, components, variance = pca_fit(vectors, dims)
    return (vectors - mean) @ components.T, variance


def umap_model(dims: int, params: dict, seed: int):
    import umap as umap_lib  # imported late: numba compiles on first import

    return umap_lib.UMAP(n_components=dims, random_state=seed, n_jobs=1, **params)


def cluster_terms(texts: list[str], labels: np.ndarray, n_terms: int,
                  max_df: float) -> dict[int, list[str]]:
    """Class-based TF-IDF: terms frequent in one cluster and rare across the others.

    Words found in more than `max_df` of the individual texts are boilerplate.
    They join the stop words before phrases are built, so no label contains one,
    not even inside a two-word phrase.
    """
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer

    clusters = sorted(k for k in set(labels.tolist()) if k != -1)
    if not clusters:
        return {}
    token = r"(?u)\b[a-zA-Z][a-zA-Z-]{2,}\b"
    words = CountVectorizer(stop_words="english", token_pattern=token, binary=True).fit(texts)
    share = np.asarray(words.transform(texts).sum(axis=0)).ravel() / len(texts)
    boilerplate = {str(w) for w, f in zip(words.get_feature_names_out(), share) if f > max_df}
    docs = [" ".join(t for t, k in zip(texts, labels) if k == c) for c in clusters]
    vectorizer = CountVectorizer(stop_words=sorted(ENGLISH_STOP_WORDS | boilerplate),
                                 ngram_range=(1, 2), min_df=2, token_pattern=token).fit(texts)
    counts = vectorizer.transform(docs).toarray().astype(float)
    tf = counts / counts.sum(axis=1, keepdims=True).clip(min=1)
    idf = np.log(1 + counts.sum(axis=1).mean() / counts.sum(axis=0).clip(min=1))
    scores = tf * idf
    vocab = vectorizer.get_feature_names_out()
    return {c: [str(vocab[j]) for j in np.argsort(-scores[n])[:n_terms] if scores[n, j] > 0]
            for n, c in enumerate(clusters)}


# --- the anchor: fitted models and the coordinates they gave the anchored ideas ---------

def _params_key(params: dict) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]


def _vectors_key(vectors: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(vectors, dtype=np.float32).tobytes()).hexdigest()[:16]


def fit_anchor(vectors: np.ndarray, ids: list[str], params: dict) -> dict:
    from sklearn.cluster import HDBSCAN

    seed = params["seed"]
    cluster_params = {k: v for k, v in params["cluster_umap"].items() if k != "n_components"}
    models = {
        "umap3d": umap_model(3, params["umap"], seed).fit(vectors),
        "umap2d": umap_model(2, params["umap"], seed).fit(vectors),
        "cluster": umap_model(params["cluster_umap"]["n_components"], cluster_params, seed).fit(vectors),
    }
    labels = HDBSCAN(**params["hdbscan"], copy=True).fit_predict(models["cluster"].embedding_)
    mean, components, variance = pca_fit(vectors, 3)
    return {
        "ids": list(ids),
        "params_key": _params_key(params),
        "vectors_key": _vectors_key(vectors),
        "models": models,
        "coords": {name: m.embedding_ for name, m in models.items()},
        "labels": labels,
        "pca": {"mean": mean, "components": components, "variance": variance,
                "points": (vectors - mean) @ components.T},
    }


def save_anchor(directory: Path, anchor: dict) -> None:
    folder = directory / LAYOUT_DIR
    folder.mkdir(exist_ok=True)
    tmp = folder / "anchor.pkl.tmp"
    tmp.write_bytes(pickle.dumps(anchor))
    os.replace(tmp, folder / "anchor.pkl")


def load_anchor(directory: Path) -> dict | None:
    path = directory / LAYOUT_DIR / "anchor.pkl"
    return pickle.loads(path.read_bytes()) if path.exists() else None


def anchor_problem(anchor: dict, vectors_of: dict[str, np.ndarray], params: dict) -> str | None:
    """Why this anchor cannot be reused, or None if it can."""
    if anchor["params_key"] != _params_key(params):
        return "the layout parameters changed"
    missing = [i for i in anchor["ids"] if i not in vectors_of]
    if missing:
        return f"{len(missing)} anchored ideas are no longer in the dataset"
    if _vectors_key(np.stack([vectors_of[i] for i in anchor["ids"]])) != anchor["vectors_key"]:
        return "the embeddings of anchored ideas changed"
    return None


def place(anchor: dict, vectors: np.ndarray, params: dict) -> dict:
    """Coordinates and cluster labels for new ideas, in the anchored space."""
    if len(vectors) == 0:
        return {"umap3d": np.zeros((0, 3)), "umap2d": np.zeros((0, 2)),
                "pca": np.zeros((0, 3)), "labels": np.zeros(0, dtype=int)}
    out = {name: anchor["models"][name].transform(vectors) for name in ("umap3d", "umap2d")}
    reduced = anchor["models"]["cluster"].transform(vectors)
    base = anchor["coords"]["cluster"]
    k, agree = params["place"]["k"], params["place"]["agree"]
    labels = []
    for point in reduced:
        nearest = np.argsort(np.linalg.norm(base - point, axis=1))[:k]
        votes = [int(anchor["labels"][n]) for n in nearest if anchor["labels"][n] != -1]
        best = max(set(votes), key=votes.count) if votes else -1
        labels.append(best if votes.count(best) >= agree else -1)
    out["labels"] = np.array(labels, dtype=int)
    out["pca"] = (vectors - anchor["pca"]["mean"]) @ anchor["pca"]["components"].T
    return out


def compute(anchor: dict, placed: dict, new_ids: list[str], ids: list[str],
            texts_of: dict[str, str], params: dict) -> dict:
    """Projections and clusterings for every idea: anchored ones where they were fitted,
    new ones where the saved models place them."""
    order = list(anchor["ids"]) + list(new_ids)
    pos = {i: n for n, i in enumerate(order)}

    def joined(anchored: np.ndarray, new: np.ndarray) -> np.ndarray:
        return np.vstack([anchored, new]) if len(new) else anchored

    umap3d = joined(anchor["coords"]["umap3d"], placed["umap3d"])
    umap2d = joined(anchor["coords"]["umap2d"], placed["umap2d"])
    pca_points = joined(anchor["pca"]["points"], placed["pca"])
    labels = np.concatenate([anchor["labels"], placed["labels"]]) if len(new_ids) else anchor["labels"]
    fitting = {"fitted_on": len(anchor["ids"]), "placed": len(new_ids)}

    def as_coords(points: np.ndarray) -> dict[str, list[float]]:
        return {i: [round(float(x), 4) for x in points[pos[i]]] for i in ids}

    variance = anchor["pca"]["variance"]
    umap_params = {**params["umap"], "random_state": params["seed"], **fitting}
    projections = {
        "umap3d": {"label": "UMAP 3D", "method": "umap", "dims": 3, "source": "essence",
                   "params": umap_params, "coords": as_coords(umap3d)},
        "umap2d": {"label": "UMAP 2D", "method": "umap", "dims": 2, "source": "essence",
                   "params": umap_params, "coords": as_coords(umap2d)},
        "pca3d": {"label": "PCA 3D", "method": "pca", "dims": 3, "source": "essence",
                  "params": fitting, "explained_variance": variance,
                  "coords": as_coords(pca_points)},
        "pca2d": {"label": "PCA 2D", "method": "pca", "dims": 2, "source": "essence",
                  "params": fitting, "explained_variance": variance[:2],
                  "coords": as_coords(pca_points[:, :2])},
    }

    # Number clusters by size, largest first, so ids are stable and readable.
    in_order = np.array([labels[pos[i]] for i in ids])
    ranked = sorted((k for k in set(in_order.tolist()) if k != -1),
                    key=lambda k: (-int((in_order == k).sum()), k))
    renumber = {old: new for new, old in enumerate(ranked)} | {-1: -1}
    final = np.array([renumber[k] for k in in_order.tolist()])
    terms = cluster_terms([texts_of[i] for i in ids], final, params["terms"],
                          params["terms_max_df"])
    clusterings = {
        "hdbscan": {
            "label": "HDBSCAN on UMAP-10",
            "method": "hdbscan",
            "params": {"hdbscan": params["hdbscan"], "umap": params["cluster_umap"],
                       "random_state": params["seed"], "place": params["place"], **fitting},
            "assignments": {i: int(k) for i, k in zip(ids, final)},
            "clusters": [{"id": k, "size": int((final == k).sum()), "terms": terms.get(k, [])}
                         for k in range(len(ranked))],
        }
    }
    return {"projections": projections, "clusterings": clusterings}


def enrich(directory: Path, params: dict | None = None, refit: bool = False) -> tuple[dict, str]:
    """Add projections and clusterings to `<directory>/dataset.json`, in place.

    Returns the enriched dataset and a sentence saying how the layout was obtained.
    """
    params = params or PARAMS
    data = load_dataset(directory)
    ids = [i["id"] for i in data["ideas"]]
    vectors, _ = load_embeddings(directory, ids)
    if vectors is None:
        message = f"{directory}: enrich needs embeddings.npy and embeddings.json beside it"
        raise ContractError([message])
    vectors = np.asarray(vectors, dtype=np.float32)
    vectors_of = dict(zip(ids, vectors))
    texts_of = {i["id"]: i.get("essence") or i["text"] for i in data["ideas"]}

    anchor = None if refit else load_anchor(directory)
    reason = "asked to refit" if refit else "no saved layout yet"
    if anchor is not None:
        problem = anchor_problem(anchor, vectors_of, params)
        if problem:
            anchor, reason = None, problem
    if anchor is None:
        anchor = fit_anchor(vectors, ids, params)
        save_anchor(directory, anchor)
        status = f"fitted a new layout on {len(ids)} ideas ({reason})"
    else:
        status = f"kept the layout fitted on {len(anchor['ids'])} ideas"

    anchored = set(anchor["ids"])
    new_ids = [i for i in ids if i not in anchored]
    new_vectors = (np.stack([vectors_of[i] for i in new_ids]) if new_ids
                   else np.zeros((0, vectors.shape[1]), dtype=np.float32))
    placed = place(anchor, new_vectors, params)
    if new_ids:
        status += f", and placed {len(new_ids)} new ideas into it"
    result = compute(anchor, placed, new_ids, ids, texts_of, params)

    enriched = copy.deepcopy(data)
    enriched.update(result)
    problems = check(enriched)
    if problems:
        raise ContractError(problems)
    target = directory / DATASET_FILE
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(enriched, ensure_ascii=False, indent=1, allow_nan=False) + "\n",
                   encoding="utf-8")
    os.replace(tmp, target)
    return enriched, status
