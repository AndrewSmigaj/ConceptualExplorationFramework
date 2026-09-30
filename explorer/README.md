# Idea Explorer

A local web app for exploring a set of ideas:
- the whole cloud, with its clusters;
- colour and size by any declared value;
- every scorer's scores side by side;
- lineage and merges;
- figures defined as presets over the same data;
- a blind rating screen whose results feed back in as another scorer.

Why it exists and what it may and may not do: [decision 0005](../docs/decisions/0005-explorer-app.md).

## How it fits together

```
producer (e.g. a pilot's export script)
    └─> <dataset>/dataset.json         read-only, validated against schema/dataset.schema.json
        <dataset>/embeddings.npy|json  optional: one vector per idea, used by enrich
        <dataset>/sessions/            blind rating sessions (ids and slots; the key)
        <dataset>/annotations/         written only by the server: ratings, notes
        <dataset>/.layout/             the fitted layout models (git-ignored)

explorer/
  __main__.py      uv run python -m explorer <validate|enrich|serve>
  contract.py      loads a dataset and checks it (schema + cross-references)
  enrich.py        anchored UMAP and PCA projections, HDBSCAN clusters with c-TF-IDF labels
  sessions.py      blind rating rules: blind view, append-only ratings, reveal, key
  server.py        FastAPI: /api plus the built frontend
  schema/          the versioned data contract
  web/             Vite + Svelte + TypeScript frontend
```

**The explorer is domain-neutral.** It never names a domain's models, arms, judges or rubric dimensions; it renders what the dataset declares. `tests/explorer/test_contract.py` fails if a domain name leaks into explorer code.

## The contract, in brief

`schema/dataset.schema.json` is the authority. A dataset declares these:

| Part | What it holds |
| --- | --- |
| `meta` | title, provenance (producer, input hashes), context documents, and the rubric with each dimension's range and direction (`higher`, `lower` or `neutral`) |
| `scorers`, `generators` | who scored and who wrote. A scorer can name the generator it shares an identity with, so "scored by its own author" is a generic concept |
| `fields` | facets (categorical), metrics (numeric) and texts (free text: shown and searched, never used to colour), optionally one value per scorer. A metric marked `sequence` gives the order ideas were produced in; Explore replays growth along it |
| `ideas` | text, essence, author, parents, run, facet and metric values, per-scorer values, and scorings |
| `runs`, `edges`, `presets` | provenance rows, lineage and merge links, and named figure configurations |
| `projections`, `clusterings` | written by `enrich`: fixed-seed coordinates and cluster assignments |

## Figure presets

A dataset defines its figures as `presets`: `{id, title, caption, kind, spec}`. The explorer draws four kinds; everything in `spec` refers to what the dataset declares, and `contract.py` checks every reference.

**References** name a value on an idea: `{"metric": id}`, `{"field": id}` (a facet), `{"per_scorer": id}` (a per-scorer field, read for the scorer in context), `{"dim": id}` (a rubric dimension of that scorer's scoring), or `{"dim_product": [id, id]}`. Any reference may carry a `label`.

**Conditions** (`where`) map a facet id, `author`, or `metric:<id>` (with an inclusive `[low, high]`) to the value or values to keep.

| Kind | Spec |
| --- | --- |
| `projection` | `projections` (ids, first is the default), `color` (a facet reference), `scorers` (choices for per-scorer colour), `marks` (`{label, where, symbol}`: a shape for matching ideas) |
| `scatter` | `panels` (one per scorer), `x` and `y` (lists of references; the first is the default), `split` (`"author"` or a facet reference: one binned-mean line per group), `bins`, `jitter`, `filters` (`{id, label, where}` toggles) |
| `table` | `rows` (`{"field": id}`), `columns` (`{"kind": "count"}`, `{"kind": "per_scorer_counts", "per_scorer": id, "scorers": [...]}`, `{"kind": "median", "ref": ...}`), `footnotes` |
| `paired` | `panels` (scorers), `reference` (the scorer each is compared with), `x` (a per-scorer facet reference), `y` (references) |

Colours follow the dataviz method: identity colours (generators, then human scorers) take the first three validated categorical slots and never cycle; ordered facets take a one-hue ordinal ramp; dark mode has its own steps. Every figure has a table view and PNG/SVG export.

**Held back.** While a rating session is unrevealed, `/api/dataset` leaves out its ideas and every idea joined to them by an edge kind the dataset declares a duplicate, so no figure or tooltip can give a blind item away. The Figures page says how many are held back.

## Running it

Python dependencies are in the `explorer` uv group, installed by a plain `uv sync`. For the frontend, run this once:

```bash
cd explorer/web && npm install
```

On the Windows drive the first install is slow (about 12 minutes, because every small file crosses the WSL boundary). Later installs are incremental.

**Start the app** (from the repo root), then open http://localhost:8765 in any Windows browser:

```bash
uv run python -m explorer serve <dataset-dir>
```

Stop it with Ctrl+C. The server rereads `dataset.json` when it changes, so a re-export shows up without a restart.

**Blind rating.** Sessions are listed on the start page. Each item is rated on the rubric's dimensions; Enter moves to the next field and, on the last one, saves and moves on. Every save is appended to `annotations/ratings/<session>.jsonl`. "Finish and reveal" needs every item rated, locks the session, and shows where each item came from beside the models' scores. The server enforces the blindness: until the reveal it sends the rating screen only the context, the rubric and the texts.

| Task | Command (from the repo root) |
| --- | --- |
| Check a dataset | `uv run python -m explorer validate <dataset-dir>` |
| Add projections and clusters | `uv run python -m explorer enrich <dataset-dir>` (about 30 s the first time for 1,100 ideas) |
| Redraw the map from scratch | `uv run python -m explorer enrich <dataset-dir> --refit` |

**The map stays put.** The first `enrich` fits the layout and saves the fitted models in `<dataset>/.layout/`. Later runs keep every existing idea exactly where it was and place new ones (a new arm, say) into the same space, so you can watch them land among the old. A new idea joins a cluster when at least 3 of its 5 nearest existing neighbours share one. The layout is refitted automatically, with a message, if an existing idea disappears, its embedding changes, or the parameters change. `--refit` does it on purpose.
| Type-check the frontend | `cd explorer/web && npm run check` |
| Build the frontend (after changing it) | `cd explorer/web && npm run build` |
| Frontend with live reload | `cd explorer/web && npm run dev` (with `serve` running; open the URL it prints) |
| Tests | `uv run pytest` |
| Browser tests (built frontend, headless Chromium) | `uv run pytest -m browser` (first time: `uv run playwright install chromium`) |

The pilot's dataset, which was built by an export script in the (private) pilot experiment, is not published. Any dataset that follows the contract works the same way.

## Milestones

Each milestone gets its own branch, and the user reviews each exit before the next one starts.

| | Milestone | Exit |
| --- | --- | --- |
| E0 | Foundations: decision 0005, contract v1 and `validate`, scaffold | Tests, check and build are green |
| E1 | Data: the pilot's re-tier, export adapter, `enrich` (UMAP, PCA, HDBSCAN), the blind rating sample | The pilot's dataset validates, and its reconciliation assertions pass |
| E2 | Server and Rate screen, with blindness enforced by the server | The user has rated the ten |
| E3 | Figures: a generic engine plus presets, the preset grammar settled, and held-back ideas for unrevealed sessions | The proposal's Figures 1–3 and Table 1 render and export |
| E4 | Explore: the 3D cloud, layers, growth, lineage, clusters, colour by any value or a blend of two, the detail panel; an anchored layout | 1,000+ points stay responsive |
| E5 | Table and Runs, each with a figure; retire the pilot's old page; browser tests | Totals reconcile across screens |

## The screens

- **Start:** the dataset and its blind rating sessions.
- **Rate:** blind rating, one item at a time, with keyboard entry. The reveal compares you with every scorer, measures your consistency on silent repeats, and allows typo corrections with a reason.
- **Explore:** the whole cloud in 3D or 2D, UMAP or PCA.
  - Layers of any facet, stepped in order or played.
  - Growth along the sequence field.
  - Lines from each idea to what it grew from.
  - Colour by any group, a red–blue gradient of one value, or a blend of two.
  - Search, filters, clusters, and a detail panel on click.
  - "Open these in the table" sends what is shown to the Table.
- **Table:** any columns, sorted, searched, CSV. A chart of the sort column across the rows in view, and details on click.
- **Figures:** the dataset's presets, each with a table view and PNG/SVG.
- **Runs:** every run as a dot by group and author, totals checked against what is in view, and "Show in Explore" per run.
