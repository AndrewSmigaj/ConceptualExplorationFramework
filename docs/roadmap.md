# Roadmap

> **Provisional.** This roadmap will be regenerated from `design.md` once the design reaches v1.0. Until then, treat it as a starting point, not a commitment.

## Stages

| Stage | What | Status |
| --- | --- | --- |
| A | Organize the repo: docs, decision records, the open-issues register, inputs | Done |
| B | Write `design.md`: outline, then first draft, then iteration rounds to v1.0 | Not started |
| C | Build, milestone by milestone | Not started |

## How milestones work

- **Each milestone** has a goal, entry criteria, deliverables, tests, human tasks and exit criteria.
- **Branches.** One git branch per milestone, merged to `main` at exit.
- **Entry.** A milestone doesn't start while an [open issue](open-issues.md) that blocks it is still Open.
- **Exit.** The exit criteria are met; `uv run pytest` is green (excluding `live`); live checks are recorded in an exit note; the user has reviewed it.

## Changes from the brief's build order (§16)

- **An M0 spike comes first.** It decides the call path ([OI-01](open-issues.md)), and trace logging depends on that.
- **Pure maths moves forward into M1.** That covers fitness, Pareto, quotas and cap arithmetic, none of which needs a model call.
- **The second domain pack's config loads in M1.** It acts as a cheap detector for domain names leaking into the core.
- **Tier 3 comes before the tier-2 calibration** ([OI-29](open-issues.md)). The anchor categories exercise caps that exist only at tier 3.
- **Random-assignment and state-vector logging start at round 1** ([OI-46](open-issues.md)), not at step 13.
- **A throwaway scatter plot appears in M4.** It's needed for the baseline and arm-separation sanity checks, long before the full viewer.
- **The viewer started early, as `explorer/`** ([0005](decisions/0005-explorer-app.md)). It is built in milestones E0–E5 and fed by the pilot first. M13 then becomes core writing the explorer's dataset contract.
- **Token cost is measured again in M8.** Readers and judges dominate cost, and M3's measurement doesn't cover them.

## Milestones

| # | Milestone | Key deliverables | Human task | Exit criteria | Status |
| --- | --- | --- | --- | --- | --- |
| M0 | Environment and dispatch spike | See below | Approve the call-path decision | Decision record written; trace schema frozen | — |
| M1 | Core foundations (no model calls) | Pydantic schemas; config loaders; safe expression language; N-axis geometric mean; N-axis Pareto; quotas and fill order; formula-driven caps; event log and snapshots; idempotent ingest. Loads the critique pack **and** the B.1 game-design config as a leak detector | — | A.8 cap tests pass: 0.525 → 0.4725; 0.175 → 0.14; zero only when correctness < 0.5; implied and priced-in gives 0.375. Tests pass with 1, 3 and 5 arbitrarily named axes. A lint test finds no pack strings in `core/`. Quotas: size 1→3, 10→3, 11→4, 20→6 | — |
| M2 | Operator registry (can run alongside M1) | Every CEFM operator verbatim in `registry.yaml`; scopes; the manual issues resolved; six chains (C.5 is meta); Appendix D metrics and bands | Review the transcription | A script diff against the manual extract shows no differences; the user signs off | — |
| M3 | Traces, prompt renderer, first calls | Trace writer (every call, from the first); stable prompt hash; replay stub; renderer for self-contained prompts; dispatch list; ingest that counts rejects as outcomes; 5 roots | — | 100% of calls traced; replay reproduces the request; tokens per call recorded | — |
| M4 | Tiers 0 and 1, dedup calibration | Quote and arithmetic verification; essence writer; embeddings on GPU (pinned model with a 512-token limit or more); a `direct` batch of about 100; CLI labelling tool; throwaway scatter plot | Label 50 dedup pairs | Threshold chosen with a loose bias; regression test on cached embeddings; A.9 baseline-tightness check | — |
| M5 | Seeding strategies and baseline arm | Strategy prompts (frozen); `seeds/` intake for text and images; baseline at about 5% of budget; `off_distribution` by kNN (leave-one-out, with centroid fallback) | Write human seeds | Local saturation curve; reference cloud | — |
| M6 | Round 1 and anchors | Uniform random operator assignment, with the state vector and hypotheses logged at every application; exhaustive expansion at tiers 0–1; blind anchor tool | Rate 12 calibration and 12 drift anchors; write synthetic anchors only if an A.7 category is missing | Anchors cover all three A.7 categories | — |
| M7 | Tier 3 panel and judge | Readers in phases (adversary before defender); mechanical checks on reader quotes; per-lens aggregation; judge with caps recomputed by the script; escalation; strangeness; model split by role | — | A.8 packets pass the band check about 5 times per prompt change; anchor correlation recorded | — |
| M8 | Tier 2 screening judge and budget | Screening prompt; calibration against the anchors and against tier 3 on 40 or more ideas; tokens per reader and judge; per-cycle budget; batched-versus-single test | — | Spearman ≥ 0.6 against tier 3; budget recorded in `project.yaml` | — |
| M9 | First full cycles | Families (hierarchical, with dendrogram paths); stratified culling; selection (softmax, per-family guarantee, 25% uniform reserve); both arms and migration; fresh starts; cycle entry point; §10.2 diagnostics; judge-drift check | — | 3 small cycles; clean diagnostics; no family collapse | — |
| M10 | Operator statistics | §8.6 table from random-assignment rows only; hypothesis splits; Appendix D metrics; lineage credit; shrinkage and Thompson sampling computed but not driving selection; Meta-Reflection pass | Review hypothesis translations | Statistics reproduce from the logs alone | — |
| M11 | Collisions and multi-operator modes | Collisions (half cross-arm); interpolation score; chains with stop distribution; colony draws; pool-scope operators | — | The A.8.4 collision case behaves as described | — |
| M12 | Governance | L7-02 phase detection and mix adjustment; shrinkage, Thompson sampling and lineage credit switched on at 30 or more random samples per operator | — | The random reserve still samples uniformly (tested) | — |
| M13 | Viewer | Standalone HTML with data inlined as JS; UMAP 3D and 2D plus a PCA toggle; stable layout across the slider; the §13 controls | — | Opens offline; arm-separation check done | — |
| M14 | Tournament and export | Pairwise judging with swapped orderings (disagreement is a tie); Bradley–Terry; `export/review-<project>.md` | Review the export | Top N per arm exported | — |
| M15 | Second domain pack, end to end | B.1 or B.2 | — | Zero changes to core or agent files (the brief's §2 acceptance test) | — |
| R | Replay and surprisal track (parallel, after M3) | A local open-weights model that fits 16 GB (quantized as needed); token surprisal; residual-stream capture | — | Surprisal stored separately from baseline distance | — |

## M0 in detail

**Environment**
- uv with Python 3.12.
- PyTorch with CUDA 12.8 or later. The RTX 5070 Ti is Blackwell and needs recent wheels.
- A sentence-transformers smoke test on the GPU.

**The spike** sends the same 5 generator calls down two paths:
- **(a)** The main session dispatches subagents from a dispatch list.
- **(b)** Python calls `claude -p` on the subscription login, with:
  - `--system-prompt-file`;
  - inline content;
  - minimal `--tools`;
  - `--json-schema` and `--output-format json`;
  - an isolated working directory.

**It measures:**
- **Trace fidelity:** can the exact prompt and completion be reconstructed?
- **Isolation:** a canary in a project `CLAUDE.md`, and the `system/init` event checked for user-level skills, memory or hooks ([OI-02](open-issues.md)).
- Token accounting, latency, concurrency, and rate-limit behaviour.

If subagents win, raise `cleanupPeriodDays` and harvest transcripts every cycle.
