# Engineering design

- **Status: outline.** Section headings and their intent only. No resolutions are written yet.
- **Companion to [`brief.md`](brief.md).** The brief says what the system is for and why. This document says how it is built, and settles every row in [`open-issues.md`](open-issues.md).

## Revision log

| Version | Date | What changed |
| --- | --- | --- |
| outline r3 | 2026-09-19 | After a traceability audit of the brief. Gave owners to the search-control layer (colony draws, governance, shrinkage), per-strategy and lineage statistics, the frame contract, the subagent definition files, and Appendix A's own run-time checks. Split selection from statistics. Added end-of-run analysis. Six new register rows, OI-58 to OI-63 |
| outline r2 | 2026-09-19 | Split the oversized evaluation section into four. Added run manifest; budget, saturation and stopping; failure and resume; the local-model track; the pack contract; a glossary. Trimmed the milestone plan to a gating list |
| outline r1 | 2026-09-19 | Section structure, for review before any prose is written |

## How to read this

- Each section lists the open issues it **Resolves**. Every row in the register is owned by exactly one section, so nothing falls between them.
- Each resolution is marked **Proposed** while it is a recommendation, and **Decided** once the user accepts it. A Decided resolution links its decision record.
- Where a resolution changes the brief's intent rather than its engineering, it also amends the brief.
- Terms are defined once, in [Appendix A](#appendix-a-glossary).

---

## 1. Scope

What this document covers, what stays in the brief, and what a reader should read first. States the three purposes the design serves at once (producing ideas, measuring the operators, interpretability) and the acceptance test: a new domain pack needs no change to core code and no change to the subagent definitions.

*Resolves: none.*

## 2. Invariants

The properties that must hold everywhere, each with the test that would catch a violation:
- domain neutrality, and the lint test for pack strings in core;
- contamination control;
- archive, never delete;
- verbatim, replayable traces;
- a raw score is a filter, never a ranking;
- anything promoted to tier 3 is judged fresh, never by reusing its tier-2 figure;
- human seeds compete on the same terms as everything else;
- one model family means no claim of judge-panel diversity in any write-up;
- any core function taking exactly two scores is a bug.

*Resolves: none. The schema that makes neutrality possible is §6.*

## 3. Architecture, the call path, and the subagent definitions

Components and what owns state; the process model; the call path, pending the M0 spike, chosen against contamination control, trace fidelity and replayability on a local model at once; how a cycle is started; and the `.claude/agents/*.md` definitions, whose genericness is the second half of the §2 acceptance test.

*Resolves: OI-01 (call path), OI-03 (orchestrator context growth).*

## 4. Isolation and contamination

What each model call is allowed to see, and how that is enforced by construction rather than by instruction. Covers the isolation of `claude -p` under a subscription login, where `--bare` is unavailable.

*Resolves: OI-02.*

## 5. Data model, state and layout

The idea record, core fields against domain fields, which fields are events and which are derived, snapshots, the single writer, atomic writes, the storage format, and the repo and `core/` module layout.

*Resolves: OI-08 (event log and snapshots), OI-09 (per-arm `combined`), OI-30 (who sets `kind`), OI-31 (fields with no producer, and the merge rule for bodies), OI-60 (producers with no schema field), OI-61 (`translation`: "none" against null).*

## 6. Configuration: packs, strategies, frames, operators

The schemas for domain, lenses, project, operator registry, chains, **seeding strategies** and **frames**. The **pack contract**: what a pack may declare, what it may mark unsupported, and what it may never override, which is the §2 acceptance test in concrete form, including the role mappings that keep domain names out of the core. Registry provenance: text verbatim from the manual, ids stable across its rewrite. And one safe expression language for formulas, caps, `zero_when`, hypotheses and `stop_when`.

*Resolves: OI-12 (role mappings for the domain-specific roles the core would otherwise name), OI-13 (the expression language), OI-42 (`preconditions` and `hypothesis` are one field).*

## 7. The model-call layer

Prompt rendering, dispatch, output contracts, tolerant parsing, how a reject is recorded, models pinned per role, concurrency and pacing. Inputs may include images, because a human seed can be a picture. Includes the inventory of every prompt the system needs and which section owns each one.

*Resolves: OI-10 (model pinning), OI-15 (malformed output, and rejects recorded as outcomes; §17 owns what the estimator does with them), OI-16 (the missing prompts), OI-54 (throughput under the subscription; the budget model is §20).*

## 8. Traces, replay and the local-model track

The trace record for the chosen call path, the stable prompt hash, and what is kept where for how long. **What the interpretability goal demands of everything upstream**: a trace has to replay as one self-contained prompt on a local open-weights model, which is what makes token surprisal and per-operator trajectory capture possible. If the call path can't produce that, the interpretability purpose in brief §1 is lost.

*Resolves: OI-11 (trace schema), OI-14 (retention and backup).*

## 9. The run manifest

What is recorded for every run so its numbers can be interpreted later: prompt hashes, thresholds, model ids, the operator registry and domain pack versions, the embedding model, and the code commit. Traces record calls; this records the configuration those calls ran under.

*Resolves: OI-55.*

## 10. The cycle pipeline

The corrected order of a cycle, round 1's exception, fresh-start epochs, and how human seeds enter at any time.

*Resolves: OI-04 (loop order against the tiers), OI-50 (fresh starts, the seeds watcher, and the cycle entry point, which follows from §3's call path), OI-57 (below).*

### 10.1 Round 1

Why nothing is scored until the operators have had a pass, and what differs from a normal cycle.

### 10.2 Failure, resume and idempotency

What happens to a cycle interrupted mid-dispatch or mid-ingest: what is safe to re-run, what must never be counted twice, and how a partially filled inbox is reconciled without corrupting operator statistics.

## 11. Evaluation: tiers 0 to 2

Schema validation, quote and arithmetic verification, normalization, the essence, embedding, deduplication, and the screening judge.

*Resolves: OI-05 (who writes the essence, and when), OI-06 (what tier 0 can actually check), OI-07 (quote normalization), OI-27 (embedding model and its token limit).*

## 12. The reader panel and the judge

Reader phases and ordering, the closed set of aggregation rules, the judge's steps, caps recomputed by the script, escalation, and the strangeness lens's placement and inputs.

*Resolves: OI-17 (partial against full concession), OI-18 (concessions that can't be quoted), OI-19 (escalation has no shared dimension), OI-20 (one reader per lens), OI-22 (the script recomputes caps), OI-23 (the strangeness lens; its retention effects are §15), OI-58 (the aggregation vocabulary isn't a closed set of aggregations).*

## 13. Calibration and drift

The anchor sets and their sizes, blind rating, the tier-2 against tier-3 check and its sample size, the judge-drift check, the repeated tier-3 judging that estimates judge variance, and the order in which the tiers are built.

*Resolves: OI-28 (anchor sets and sample sizes), OI-29 (tier 3 before the tier-2 calibration), OI-63 (nothing schedules the re-judging the shrinkage factor needs).*

## 14. The tournament

Pairwise judging with swapped orderings, ties, and Bradley-Terry, with a ranking question for each arm.

*Resolves: OI-48 (the pairwise prompt favours the rational arm).*

## 15. Fitness, retention and families

The axes and how `off_distribution` is measured and combined; the geometric mean and its floor; the Pareto rule; cluster quotas; the strangeness floor and cull exemption; and how families are recomputed.

*Resolves: OI-21 (the paths to zero, and normalization), OI-25 (baseline distance measured against itself), OI-26 (combining the two `off_distribution` measurements), OI-36 ("near the cull line"), OI-38 (dendrogram linkage and cut), OI-59 (when a covariance can be fitted, and the fallback).*

## 16. Selection and the scheduler

Parent selection and its reserve; operator scope as the only gate; the dispatch modes (single, chain, colony) and their shares; shrinkage applied to the value parents are drawn on; and the governance layer that sets the per-cycle mix from measured behaviour only, never from the manual's taxonomy, and that must not disturb the uniform reserve.

*Resolves: OI-33 (Thompson sampling), OI-40 (`coherence_loss` for chains), OI-45 (the two 25% reserves), OI-51 (the manual's own contradictions), OI-52 (operators that act on a system, not an idea).*

## 17. Operator and strategy statistics

The state vector logged at every application; hypotheses recorded and never enforced; lift, its definition and its estimator, counting rejects and using random-assignment rows only; the same table per seeding strategy, where a strategy's lift is its children's; lineage credit; per-reader predictive validity against eventual lineage value; and the Meta-Reflection pass at each epoch's end.

*Resolves: OI-34 (refine-like lift), OI-35 (the hit-rate threshold), OI-43 (the lift definition), OI-46 (logging starts at round 1), OI-47 (samples per operator), OI-62 (Meta-Reflection, and what an epoch is).*

## 18. Arms, baseline and collisions

What differs between the arms, the migration rule, the baseline arm as both control and reference cloud, and collisions including cross-arm.

*Resolves: OI-24 (baseline against the `direct` strategy), OI-32 (fair cross-arm comparison), OI-37 (the collision floor), OI-39 (the interpolation score), OI-44 (migration before shrinkage exists), OI-49 (collision frequency).*

## 19. Metrics and diagnostics

What is logged every cycle, the CEFM Appendix D metrics under the manual's own names, phase detection, the per-arm distributions the first-run sanity checks need (locator verdicts, priced-in rate), and the alarms that say a run has gone wrong.

*Resolves: OI-41 (phase detection, the Appendix D bands, and the governance rules that consume them).*

## 20. Budget, saturation and stopping

What a cycle costs and what a run costs, in tokens and in wall-clock hours under a subscription; the knobs that control it; the saturation signal and what happens when it flattens; and how remaining budget shifts from generating to refining.

*Resolves: OI-56.*

## 21. End-of-run analysis

The one-off analysis that answers the project's own question: cluster every arm together in a common space, count the families each arm reached, and report the curve of families discovered per 1000 tokens rather than a single number. Plus the secondary results, including the share of top ideas whose lineage includes a human seed, and what round 1 says about the seeding strategies.

*Resolves: none; the fairness constraints are OI-32 in §18.*

## 22. Viewer and export

The standalone viewer, how its data is loaded and laid out, and the review export.

**Proposed** ([0005](decisions/0005-explorer-app.md)):
- The viewer is `explorer/`, a local-server web app that reads a versioned dataset contract, `explorer/schema/dataset.schema.json`.
- Core writes that contract, as the pilot's adapter already does.
- Serving over localhost replaces inlining the data as JS.
- Projections are computed once with fixed seeds, which keeps the layout stable.

*Resolves: OI-53 (viewer data loading, stable layout, level of detail).*

## 23. Testing strategy

What is tested deterministically with no model call, what needs recorded fixtures, and the few live checks. Includes the worked cap examples (A.8), the collision expectation (A.8.4), the first-run sanity checks (A.9), and the diff of the operator registry against the manual.

*Resolves: none.*

## 24. Human-in-the-loop work

The tools a person needs: the dedup labelling tool, the blind anchor rater, the seeds dropbox, and the export review.

*Resolves: none; see [`human-tasks.md`](human-tasks.md).*

## 25. Risks

What is most likely to go wrong, beyond the brief's own list, and what would detect each one early.

*Resolves: none.*

## 26. What gates what

The dependency order this design implies: which components must exist before which others, and which human tasks gate which. [`roadmap.md`](roadmap.md) is the single schedule and is regenerated from this section.

*Resolves: none.*

---

## Appendix A. Glossary

One definition each, used consistently everywhere including in prompts: arm, axis, chain, colony, cycle, domain pack, epoch, essence, family, fitness, frame, idea, kind, lens, lift, operator, packet, pool, reader, scope, seed, strategy, tier.
