# Open issues

This register lists the gaps, contradictions and undefined terms in [`brief.md`](brief.md) that the engineering design must resolve. It is the main input to `design.md`.

**How rows move**
- A row opens as **Open**.
- It becomes **Proposed** when `design.md` recommends a resolution.
- It becomes **Decided** when the user accepts that resolution. At that point it links its decision record and its design section.
- A milestone may not start while a row that blocks it is still Open.

**Columns**
- **§**: the section of the brief the issue comes from.
- **Blocks**: the earliest milestone the issue gates. Milestones are defined in [`roadmap.md`](roadmap.md).

## A. Architecture and state

| ID | § | Problem | To decide | Blocks | Status |
| --- | --- | --- | --- | --- | --- |
| OI-01 | 3, 3.1, 12, 14 | **Call path.** When the main session dispatches subagents, no hook exposes a subagent's full system prompt. Temperature can't be set. Transcripts are multi-turn tool-use logs that are deleted after 30 days. So §12's verbatim, replayable traces aren't guaranteed. | Main-session subagents, or Python calling `claude -p` with self-contained rendered prompts. Settled by the M0 spike. | M0 | Open, pending spike |
| OI-02 | 3.1 | **`claude -p` isolation without `--bare`.** The subscription login rules out `--bare` ([0003](decisions/0003-billing-subscription.md)). User-level `~/.claude` content (CLAUDE.md, skills, memory, hooks) may load into every call. | The flags or environment that exclude it. Verify with a canary string and the `system/init` event. | M0 | Open |
| OI-03 | 3.1 | **Orchestrator context growth.** A main session dispatching thousands of calls fills its context. Compaction then summarizes it, which is the content-composition risk §3.1 warns about. | Whether the main session dispatches at all, how many calls per session, and a restart policy. | M0 | Open |
| OI-04 | 4, 7.1 | **The loop order contradicts the tiers.** Dedup comes after Evaluate (§4 steps 5–6), but tier 2 runs on "every non-duplicate". Tier 3 selects family leaders and ideas "near the cull line", but clustering and culling come after Evaluate. | The corrected order. Candidate: tier 0 → tier 1 → dedup → tier 2 → provisional cluster → provisional cull line → tier 3 → final cull → cluster. | M1 | Open |
| OI-05 | 6.4, 7.1, A.4 | **Nothing produces the essence before dedup.** Dedup embeds the essence at tier 1, but only the judge writes one (A.4 step 4), and the generator output has no essence field. Round 1 (§4.1) can't dedup. | An essence-writer call at ingest (its model and prompt), or an essence written by the generator (not neutral). Also: may re-judging rewrite the essence? That would change what dedup matches on. | M4 | Open |
| OI-06 | 7.1, 7.2 | **Tier 0 has nothing structured to check.** Tier 0 is "script-only" and recomputes arithmetic, but the generator writes prose with no `quotes[]` or `computations[]`. A script also can't tell which claims "rest on" a quote that fails. | Add structured fields to the output contract (this changes verbatim prompts; log it in the prompt changelog), or move arithmetic to the verifier reader. | M4 | Open |
| OI-07 | 7.2, A.6 | **Quote normalization.** It must be decided before the first run: changing it later invalidates every earlier verification. The brief itself had CRLF line endings, and sources pasted on Windows may too. | Whether to normalize quote characters, whitespace and line endings at ingest, applied identically to the source and to candidate quotes. | M4 | Open |
| OI-08 | 11 | **The state model.** `ideas.jsonl` is append-only, but many fields change every cycle: per-arm `combined`, the Pareto flag, normalized `off_distribution`, `cluster`, `retained_by`, `status`. | Event log plus per-cycle snapshots; a single writer; atomic writes; JSONL or SQLite. Which fields are events and which are derived. | M1 | Open |
| OI-09 | 5.3, 9.1, 11 | **`combined` depends on the arm, but is stored once.** Migration needs the value under every arm's weights. | Store it per arm, or compute it on demand. | M1 | Open |
| OI-10 | 14, A.3, A.6 | **Models per role conflict.** §14 hardcodes models in the agent frontmatter. A.3 sets a model per reader. A.6 sets them per role, with `evidence_readers: sonnet` even though adversary, defender and repair_tester are evidence readers on opus. Aliases can also change mid-run. | One source of truth for the model per role, with full model IDs pinned. | M3 | Open |
| OI-11 | 12 | **The trace schema.** `params.temperature` can't be set or known. If subagents are used, a trace is a multi-turn tool-use transcript, not one request. | The final trace schema for the chosen call path. | M3 | Open |
| OI-12 | 2, 5.2, 7.7, 8.6, 8.8, 9.2, 11 | **Domain names leak into the core.** The core schema has critique-shaped fields: `evidence.adversary`, `defense`, `repair`, `strangeness`, `answers`, and the strategy enum. Coherence Entropy uses `correctness` and `clarity`. The §7.7 floor names a lens, a verdict and an axis. Refine needs "the adversary's objection". An axis is measured by name. Exactly two named arms are assumed. | Role mappings in `domain.yaml`, such as "objection source", "exemption rule" and "measured axis", and which fields move under `fields` and `readers`. | M1 | Open |
| OI-13 | 8.2, 8.4, 8.5, A.2 | **One expression language is needed.** It has to cover formulas (`centrality * strength`), caps, `zero_when`, hypotheses (including "over 3 cycles") and `stop_when`. A.2 doesn't say which reader supplies the key for `strength_caps`. | The grammar, the available variables, the time-window operators, and how cap keys bind to reader outputs. It must not use `eval`. | M1 | Open |
| OI-14 | 12 | **Run data retention.** Traces are "not recoverable later", but pool and trace directories are git-ignored. | A backup and retention policy for `pool/` and `traces/`. | M3 | Open |
| OI-15 | 4, 8.6 | **Malformed outputs and retries.** Model output can arrive in code fences, with extra prose, with missing fields, or over 200 words. Retrying after a failure biases the operator statistics. | Parsing tolerance, and counting rejects as outcomes of that operator. | M3 | Open |

## B. Evaluation and calibration

| ID | § | Problem | To decide | Blocks | Status |
| --- | --- | --- | --- | --- | --- |
| OI-16 | 4.1, 7.1, 7.5, 8.3, 8.5, 8.7, 9.3 | **Prompts are referenced but never given:**<br>• five seeding strategies, and how each pairs with an arm's generator prompt<br>• `direct` and baseline<br>• the screening judge<br>• the essence writer<br>• the reader wrapper (A.3 gives questions only)<br>• the escalation judge that works without the panel<br>• the chain wrapper<br>• the pool-operator wrapper<br>• Meta-Reflection | The text of each prompt. Each is frozen and hashed once written. | M4–M8 (per prompt) | Open |
| OI-17 | A.4, A.6 | **The concession cap contradicts itself.** A.6 says `scope: partial` caps strength at 0.5. The A.4 judge applies the cap only for a verified *full* concession. | Which scopes cap, and by how much. | M7 | Open |
| OI-18 | A.3, A.6 | **Some concessions can't be quoted.** C1–C3 in `problem.md` are paraphrases, and the deferred sections aren't in the source. `must_appear_in: source` therefore fails for exactly the concessions A.6 cares about. | Quote against the problem file too, cite caveats by id, or something else. | M7 | Open |
| OI-19 | 7.5, A.3, A.4 | **Escalation has no shared dimension.** It fires when evidence and scoring readers disagree on a shared dimension, and A.3 has none. Judge STEP 3 compares centrality and strength with a "panel aggregate" that the panel never produces. | Redefine the escalation trigger and the panel aggregate. | M7 | Open |
| OI-20 | 7.4, A.3 | **One reader per lens.** The `min` and `max_with_evidence` rules, and "selection uses the max across readers", do nothing unless a lens is read more than once. | Replicate some readers, or drop those rules. | M7 | Open |
| OI-21 | 5.3, A.8.3 | **There are several paths to zero.** A.8.3 says correctness is the only path to zero. But centrality 0 or raw strength 0 also give zero, and a pool-normalized `off_distribution` minimum is exactly 0, which makes the geometric-mean `combined` zero. | An epsilon floor and the normalization scheme. | M1 | Open |
| OI-22 | A.4 | **The judge does the cap arithmetic (STEP 2).** | The script recomputes caps from the judge's components, so the A.8 cases become a deterministic test. | M7 | Open |
| OI-23 | 7.3, 7.7, A.3 | **The strangeness lens doesn't fit its role.**<br>• It asks "if this scores low", but readers see no scores.<br>• It runs only at tier 3, which low scorers rarely reach.<br>• Its floor writes a judged verdict into the axis §7.7 keeps out of the judge's hands. | Its placement, its inputs, and how its effect is applied. | M7 | Open |
| OI-24 | 4.1, 9.3 | **Baseline versus the `direct` strategy.** `direct` is the baseline arm, but round 1 expands every seed with operators, while the baseline must have no operators and no parents. | Can baseline ideas be parents? Can an operator-arm idea merge into a baseline idea? | M5 | Open |
| OI-25 | 5.2, 9.3 | **Baseline distance measures the baseline against itself.** Baseline ideas sit inside their own reference cloud, so comparing arms on this axis is biased. | Leave-one-out distance, and whether to report baseline `off_distribution` at all. | M5 | Open |
| OI-26 | 5.2 | **The two `off_distribution` measurements have no combination rule.** They are stored separately, but no rule turns them into the single axis value. Surprisal doesn't exist until the local model runs. | The combination rule, and the value to use before surprisal exists. | M5 | Open |
| OI-27 | 6.4, 13 | **Embedding model limits.** 200 words is roughly 260–300 tokens, over the 256-token limit of many sentence-transformers. | Pin an embedding model with enough context, and a truncation policy. | M4 | Open |
| OI-28 | 4.1, 7.1, 7.8, A.7 | **Anchors.**<br>• Calibration anchors come from the pool, but drift anchors are "never in the pool", so there are two sets and 24 ratings.<br>• A Spearman correlation on n = 12 is too noisy for a 0.6 threshold (95% CI roughly 0.0 to 0.88).<br>• The rater also writes the seeds, which limits how independent the judge can be. | Set sizes, the tier-2-versus-tier-3 sample (40 or more), and the independence protocol. | M6 | Open |
| OI-29 | 16, A.7 | **Anchor categories need tier 3.** The A.7 categories test the locator and concession caps, which exist only at tier 3. The brief builds tier 2 (step 8) before tier 3 (step 12). | Reorder: build tier 3 before calibrating tier 2. The roadmap already does this; it needs confirming. | M6 | Proposed in roadmap |
| OI-30 | 8.3, A.2, A.4 | **`kind` is set only by the tier-3 judge.** Ideas that stop at tier 2 have no kind, and `analysis` isn't in the pack's `kinds`. | Who sets `kind`, at which tier, and how core kinds (`analysis`) combine with pack kinds. | M7 | Open |
| OI-31 | 4, 11 | **Some fields have no producer.** Nothing produces `answers` or a collider's `translation`. "The better-worded body survives" (on merge) isn't defined. | A producer for each, or remove the field. The merge rule for the body. | M4 | Open |
| OI-32 | 9.3 | **Arm comparisons are unfair.** Secondary metrics compare baseline tier-2 scores with operator-arm tier-3 scores. The baseline gets 5% of budget against 95%. It isn't said whether "tokens" includes judging. | Run a random sample from every arm through the same tier; compare at equal budget; define the token denominator. | M5 | Open |

## C. Search and statistics

| ID | § | Problem | To decide | Blocks | Status |
| --- | --- | --- | --- | --- | --- |
| OI-33 | 16 | **Thompson sampling** appears only in the build order and is never defined. | What it samples, its prior, and what it drives. | M10 | Open |
| OI-34 | 8.7 | **"Refine-like lift"** is undefined. | The definition. | M12 | Open |
| OI-35 | 8.6 | **The hit-rate threshold** is undefined. | Its value, or a percentile of the pool. | M10 | Open |
| OI-36 | 7.1 | **"Near the cull line"** is undefined. | A band width around the provisional cull line. | M9 | Open |
| OI-37 | 4, 9.2 | **The collision floor** (on home fitness) is undefined. | Its value, or a percentile. | M11 | Open |
| OI-38 | 6.3 | **Dendrogram linkage and the per-cycle cut rule** are undefined. | Linkage method, distance, the cut rule, and the granularity levels in `cluster.path`. | M9 | Open |
| OI-39 | 10.3 | **The interpolation score formula** is undefined. | The formula from parent similarities and the distance between the parents. | M11 | Open |
| OI-40 | 8.5 | **`coherence_loss`**, the chain stop criterion, is undefined. | Whether the subagent self-reports it or it is measured, and its scale. | M11 | Open |
| OI-41 | 8.6, 8.7 | **Phase detection and the Appendix D bands.** They live in the external CEFM manual. | Transcribe the bands; define phase detection. | M12 | Open |
| OI-42 | 8.2, 8.4 | **The same field has two names:** `preconditions` in §8.2, which reads like a gate, and `hypothesis` in §8.4. | One name (`hypothesis`) and its semantics. | M2 | Open |
| OI-43 | 8.6, 10.1 | **Lift is ill-defined.**<br>• Parent and child are scored at different tiers and times, while normalization and families shift.<br>• Regression to the mean makes lift negative for strong parents.<br>• It isn't said which arm counts as home after a migration.<br>• Children can have two parents. | Same-tier score snapshots, a correction for regression to the mean, and rules for home arm and two-parent children. | M10 | Open |
| OI-44 | 9.1, 16 | **Migration is measured "after shrinkage"**, but shrinkage stays off until M12. | The migration rule before shrinkage is switched on. | M9 | Open |
| OI-45 | 8.1, 8.6 | **There are two different 25% reserves.** One is for parent selection (§8.1), the other for operator assignment (§8.6). Only random operator assignment removes the bias in operator statistics. | Clarify both, and confirm they are independent. | M6 | Open |
| OI-46 | 8.4, 16 | **Random-assignment logging starts too late.** The brief schedules it at step 13, but round 1 is step 7, so round-1 data can't feed §8.6. | Start logging the state vector and hypotheses at the first operator application. The roadmap already does this; it needs confirming. | M6 | Proposed in roadmap |
| OI-47 | 8.4, 8.6 | **Not enough samples.** At 7,500 ideas, 25% reserved, 27 operators, that's about 70 random applications per operator, before splitting by arm, hypothesis and depth. §8.4 wants 30–50 on each side. | The run size, or a per-run operator subset. | M6 | Open |
| OI-48 | 7.6, A.4 | **The pairwise prompt favours the rational arm.** It asks which idea "costs the author more". Ranking the insight arm on that question uses the other arm's goal. | A tournament question for the insight arm. | M14 | Open |
| OI-49 | 4, A.6 | **Collision frequency is inconsistent.** §4 says collide "every few cycles"; A.6 sets `collision_share: 0.15` per cycle. | Which one holds. | M11 | Open |
| OI-50 | 14, 16 | **Some work has no build step.** The cycle entry point ("check the current docs"), fresh-start epochs and the `seeds/` watcher aren't scheduled. The entry point depends on OI-01. | The mechanism, and which milestone owns each item. | M9 | Open |

## D. Operators, viewer, operations

| ID | § | Problem | To decide | Blocks | Status |
| --- | --- | --- | --- | --- | --- |
| OI-51 | 8.2 | **The manual contradicts itself.** It gives the operator count as 26 in one place and 25 in another, and its table has 27 rows. Catastrophic Grace appears twice (L4-04 and L5-03). | Merge the duplicate or differentiate it; decide the canonical list. | M2 | Open |
| OI-52 | 8.2, 8.3 | **Some operators act on a system or a research process, not on one idea.** They may produce non-ideas that fail the schema and waste budget. | The scope of each; wrappers for the ones that aren't one-idea operators. | M2 | Open |
| OI-53 | 13 | **Viewer problems.**<br>• A `file://` page can't fetch `data.json`.<br>• Re-fitting UMAP on every rebuild makes the cycle slider jump.<br>• 7,500 points with edges is heavy. | Inline the data as JS; keep the layout stable; decide level of detail. Proposed in [0005](decisions/0005-explorer-app.md): serve over localhost, with fixed-seed projections. | M13 | Open |
| OI-54 | 14, 17 | **Throughput under the subscription.** Thousands of calls, about 10 per idea at tier 3, all under plan rate limits. Wall-clock time could run to days. | Concurrency, pacing and a budget model in tokens and hours. Measure at M3 and M8. | M8 | Open |

## E. Operations and reproducibility

These three are gaps in the brief itself, found while outlining the design.

| ID | § | Problem | To decide | Blocks | Status |
| --- | --- | --- | --- | --- | --- |
| OI-55 | 12, 17 | **Nothing records the configuration a run used.** Traces record individual calls, but not the prompt hashes, thresholds, model ids, operator registry and domain pack versions, embedding model or code commit in force. Two runs weeks apart can't be compared, and a result can't be attributed to a change. | The run manifest: its contents, where it is written, and what refuses to start without it. | M3 | Open |
| OI-56 | 6.2, 17, 19 | **No rule says when a run stops.** §19 names the saturation signal (distinct families per 100 accepted ideas flattening) and says to shift the rest of the budget to refinement, but nothing defines the measurement window, the threshold, or the shift. Under a subscription the budget is also wall-clock hours, not only tokens. | The budget model, the saturation measure and threshold, and what changes when it trips. | M8 | Open |
| OI-57 | 3, 4 | **No rule for an interrupted cycle.** A crash mid-dispatch or mid-ingest leaves a partial dispatch list and a half-filled inbox. Re-running must not double-count ideas or corrupt operator statistics, which are counted per attempt. | What is idempotent, what is resumable, how a partial inbox is reconciled, and how retries are distinguished from attempts. | M3 | Open |

## F. From the traceability audit

Found on 2026-09-19 by auditing every requirement in the brief against the design outline and this register.

| ID | § | Problem | To decide | Blocks | Status |
| --- | --- | --- | --- | --- | --- |
| OI-58 | 7.4, A.3, A.4 | **The aggregation vocabulary is not a set of aggregations.** `from_defender_survives` and `from_locator_and_judge` are derivations, not rules over readers. Centrality and raw strength are assigned by the judge, so the "panel aggregate" the judge compares itself against is circular for exactly those dimensions. §7.4's lens-type table and A.3's per-lens rules don't correspond: §7.4 has no centrality. "Produced supporting evidence", which gates `max_with_evidence`, is undefined. | A closed set of rules, what each takes as input, and what the judge is compared against. | M7 | Open |
| OI-59 | 5.2 | **No criterion for Mahalanobis against kNN.** "Where the cloud is tight enough to fit a covariance" gives no test and no fallback, and a few hundred baseline points in a high-dimensional embedding space cannot support a full covariance. | The criterion, the estimator (such as shrinkage or a PCA reduction), and the fallback. | M5 | Open |
| OI-60 | 8.5, 8.7, 11, A.4, A.7 | **Fields that are produced but have no schema slot**, the inverse of OI-31: `colony_id`, `chain_stopped_at`, the collider's `used_from_a` and `used_from_b`, refine's `what_changed`, the judge's justifications for centrality and strength, and an anchor's synthetic flag with its keep-out-of-the-pool rule. | Which are core fields, which are domain `fields`, and which are run metadata rather than idea fields. | M1 | Open |
| OI-61 | A.4, A.5 | **`translation` has two representations and two producers missing.** A frame says to write "none"; the generator prompts say `null`. The collider and refine prompts omit the field although the frame requirement still applies to their output. | One representation, and whether a frame is inherited by children. | M4 | Open |
| OI-62 | 4, 8.6, 8.7 | **Meta-Reflection and "epoch" are underspecified.** An epoch bounds fresh starts, the Meta-Reflection pass and the differencing of Meta-Adaptive Gain, but is never defined beyond `fresh_start_every`. The pass's inputs, that its output is an idea with `kind: analysis`, and whether it is excluded from export, are unstated. | The definition of an epoch, and the pass's inputs, output and export treatment. | M10 | Open |
| OI-63 | 7.8, 9.1 | **Nothing schedules the re-judging that shrinkage needs.** The shrinkage factor is "estimated from tier-3 re-judging variance", and migration is measured after shrinkage, but no sample of repeat judgements is ever scheduled. | The re-judging sample: its size, its cadence, and what happens before enough data exists. | M12 | Open |
