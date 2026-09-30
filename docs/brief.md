# Idea evolver: project brief

A system for evolving ideas with Claude Code subagents. It generates ideas, perturbs them with operators, judges them through fixed lenses, merges duplicates, culls with diversity pressure, clusters the survivors into families, and lets a person browse everything.

The project name is a placeholder. This document is the whole design; there is no earlier version to reconcile against.

## 1. Purpose

The system is neutral about subject matter. A **domain pack** says what an idea is and how to judge one. A **project** points a domain pack at one concrete problem.

Intended uses so far: critiques of arguments, game design ideas, approaches to a technical or research problem.

The first real use is critiques of two arguments, specified in Appendix A. Nothing in the core may depend on it.

There are two further purposes beyond producing ideas:

- **Measuring the operators.** Do Conceptual Exploration Operators move a model past its default output, and do human seeds beat unseeded search? The run logs and the baseline arm (section 9.3) are the data.
- **Interpretability.** The same scaffolds will later run against a local open-weights model to study how scaffolding shapes internal representations and trajectories. That requires verbatim trace logging from the first call (section 12).

The system produces candidates. A person verifies and develops the ones worth keeping.

## 2. Three layers

| Layer | Holds | Changes |
| --- | --- | --- |
| Core | The loop, state, fitness machinery, selection, retention, families, evaluation tiers, viewer, subagent definitions | Rarely |
| Domain pack | What an idea is: extra fields, prompts, lenses, fitness axes, score formula, caps | Once per kind of ideation |
| Project | One problem: brief, frames, seeds, anchors, budget, arms, and the pool itself | Once per problem |

**Acceptance test for the design:** adding a domain pack must require no change to core code and no change to the subagent definitions. Build the core against the critique pack, then add a second pack to prove it.

**The rule that keeps this true:** the core never hardcodes axis names, lens names, or how many of either there are. Any core function signature that takes exactly two scores is a bug.

## 3. Architecture

A Python script owns all state. The Claude Code main session only dispatches subagents and calls the script. Subagents read their inputs from files and write their outputs to files.

### 3.1 Independence and contamination controls

These matter more than anything else in the build. Verified against the Claude Code subagent docs (https://code.claude.com/docs/en/sub-agents).

- Each subagent starts with a fresh, isolated context window and does not see the conversation history. This is what makes runs independent.
- Subagents load the project `CLAUDE.md` by default. Set `omitClaudeMd: true` on every generator, collider, reader and judge, and keep idea content out of `CLAUDE.md` entirely.
- The delegation message is written by the main session, which may have seen other ideas. The script writes a dispatch list (`dispatch/cycle-N.json`) containing file paths only; the main session copies entries verbatim and never composes idea content. Prompt text lives in the domain pack as fixed templates.
- A generator sees: the problem file, an optional frame, one operator prompt, at most one parent, and the output contract. It never sees the pool, scores, families, or other ideas.
- A reader sees: the problem file and the idea body. It never sees origin, operator, lineage, or any other score.
- Each subagent writes to `inbox/<uuid>.json` and replies with that path only. Subagent results consume main-session context, so replies must be one line.
- Generators, readers and judges do not spawn subagents. Leave `Agent` out of their `tools` list.

If prompt control through the main session proves leaky, move dispatch into the Python script using non-interactive mode, so every prompt is built from templates.

## 4. The loop

One cycle, in order:

1. **Plan.** The script selects parents (section 8.1) and writes the dispatch list.
2. **Generate.** One generator subagent per entry applies one operator and writes one child. Roots have no parent and no operator.
3. **Collide.** Every few cycles, pair ideas from different families, and from different arms, that both clear a floor. Half of all collisions are cross-arm by default.
4. **Ingest.** The script reads `inbox/`, validates against the domain schema, assigns ids and lineage.
5. **Evaluate.** Tiered, per section 7.
6. **Deduplicate.** Embed the essence. Near matches merge into the earlier idea; `convergence_count` rises by one and the better-worded body survives.
7. **Retain and cull.** Per section 6.
8. **Cluster.** Recompute families (section 6.3).
9. **Log.** Cycle record plus the diagnostics of section 10.2.

**Round 1 is different.** Seeding and the first operator round run before any fitness is assessed; see section 4.1.

**Fresh starts.** Every N cycles, an epoch of new roots, generated with the seeding strategies of section 4.1 and no view of the pool. Merged in after dedup. Limits path dependence.

**Human seeds.** A person may drop a file in `seeds/` at any time: a picture, an analogy, a half-formed objection, a finished critique. It enters as a parent with `strategy: human`. This is the highest-value input available, so it must stay trivially easy. Human seeds are not privileged in scoring or selection; they compete on the same terms as everything else, which is what makes the comparison in section 4.1 meaningful.

## 4.1 Seeding, and the first round

The pool does not start from one generator prompt. It starts from several **seeding strategies**, each producing roots independently, plus any human seeds. Strategy is recorded on every idea exactly like operator is, so it can be measured the same way.

### Strategies

Each is a separate prompt and a separate dispatch. The set below is a starting point; strategies are config, and adding one is a prompt file plus a registry line.

| Strategy | What it does |
| --- | --- |
| `human` | Seeds written by a person, entered verbatim. The highest-value input available |
| `direct` | The plain request, no scaffolding. This is also the baseline arm (section 9.3), so it doubles as the control and the reference cloud |
| `step-targeted` | One root per numbered step or structural element, forcing coverage the other strategies may skip |
| `assumption-first` | Enumerate what the argument needs to be true, then attack one item |
| `adversary-role` | Write as someone with a stake in the argument being wrong |
| `frame-seeded` | Roots generated under each frame, with the translation requirement |
| `deliberate` | The direct prompt with extended reasoning and a self-check pass before output |

Strategies are not arms. Any strategy may feed the insight arm or the rational arm, depending on which generator prompt it pairs with.

### The first round runs before fitness is assessed

Round 1 order: seed, then apply one full round of operators to every seed, and only then evaluate. Nothing is scored until the operators have had a pass.

The reason is that score-weighted selection needs scores, and a first round that evaluates before expanding would spend its whole budget deciding which seeds are good using a judge nobody has calibrated. Expanding everything first is cheaper in judge calls per unit of information, since the children carry evidence about their parents.

So round 1 differs from every later cycle:

- **Selection is exhaustive, not weighted.** Every seed is expanded, by several operators each, chosen uniformly among scope-valid ones.
- **Tiers 0 and 1 still run** on seeds and children: schema validation, mechanical verification of quotes and arithmetic, embedding, deduplication. These are script-only and do not need a calibrated judge.
- **Tier 2 and above wait** until the round is complete, then run over seeds and children together.

After that, cycles proceed normally.

### Calibration anchors come from round-1 output

Anchors for judge calibration (section 7.8) are drawn from what round 1 actually produced, not written in advance. Pick about twelve spanning the visible range and rate them by hand before the judge scores anything.

Two rules for this, both about not contaminating the result:

- **Rate blind.** Strip strategy, operator, arm and lineage from the anchor set before rating, and shuffle it. Otherwise the ratings carry an expectation about which strategies should have done well.
- **Keep your own seeds out of the anchor set.** If the judge is calibrated on ideas you rated and then used to score your own seeds, the comparison between your seeds and the evolved population is no longer independent. Rate other people's material, judge your own with it.

### What the first round answers

Beyond producing a pool, round 1 is the first real measurement:

- Which seeding strategies produced ideas that survived tier 0, and which produced ideas that operators improved.
- Whether human seeds outperform generated ones, measured as lift in their children rather than as their own scores. A seed that scores poorly and produces strong children is doing its job.
- Where the human seeds sit against the generated population once both are scored by the same judge.

## 5. Fitness

### 5.1 The vector

Each domain pack declares `N` axes. The critique pack declares two:

| Axis | Measures | How |
| --- | --- | --- |
| `off_distribution` | Distance from what the model produces by default | Measured, no reader involved |
| `task_fitness` | How well it does the job | Reader panel and judge |

### 5.2 Measuring `off_distribution`

Two independent measurements. Use both, store both separately, never average before storage.

**Baseline-cloud distance.** The baseline arm (section 9.3) is a sample from the model's default distribution for this exact problem. Off-distribution-ness is the mean distance to the `k` nearest baseline points (default `k` = 5) in embedding space, or Mahalanobis distance where the cloud is tight enough to fit a covariance. Normalized against the pool.

**Token surprisal.** Mean per-token negative log-probability of the idea text conditioned on the problem statement, under the local open-weights model, via the replay script (section 12). Normalize for length. It partly measures unusual phrasing rather than unusual content, so it is never used alone.

Disagreement is diagnostic. Far from the cloud but unsurprising token by token is a familiar thought in an unusual corner of the space, which is interesting. The reverse is odd phrasing of a default thought, which is not.

Before the baseline arm exists, fall back to normalized distance from the pool centroid and record `off_distribution_source` accordingly.

**Compute this on the body embedding, not the essence embedding.** Essences are deliberately formulaic so that dedup works, which compresses their spread. Essence embeddings are for deduplication only.

### 5.3 Combining

Ranking uses a weighted geometric mean:

```
combined = (prod_i axis_i ^ w_i) ^ (1 / sum_i w_i)
```

A product, not a sum: fitness on two axes must beat fitness on one, and a sum lets a single high axis carry an idea.

Weights are per arm, declared in the domain pack. The insight arm weights `off_distribution` higher; the rational arm weights `task_fitness` higher. Both arms carry both axes. This is the only difference between their fitness functions.

The cost of a product is that anything near zero on one axis dies regardless of the other, which is wrong for stepping stones. Section 6.1 is what fixes that. `combined` is for ranking only, never for retention on its own.

## 6. Retention, culling, families

Archive, never delete. Culled ideas get `status: archived`, stay in the file, stay visible in the viewer, stay usable in lineage. They are not drawn as parents.

### 6.1 Rule 1, pool-wide: the Pareto front is never culled

Any idea not dominated on the full fitness vector is retained regardless of cluster quotas. With two axes this set is small, and it is exactly where an idea extreme on one axis and weak on another survives. That is the stepping-stone case, and it is why the geometric mean is safe to use for ranking.

### 6.2 Rule 2, per cluster: quotas that scale, with a floor

```
quota_c = max(floor, ceil(rate * size_c))      # defaults: floor = 3, rate = 0.3
```

Scaling means a large cluster of genuinely good ideas is not pruned to the size of a thin one. The floor protects small and newly formed clusters, which is where novelty appears first.

Fill each quota in this order, skipping anything already retained by Rule 1:

1. The leader on each axis, one per axis.
2. The best `combined`.
3. A random draw from the remainder.

The random draw is not decoration. With the random reserve in selection (section 8.1), it is what keeps low-scoring stepping stones alive.

If the pool grows faster than the judging budget can follow, lower `rate` before raising `floor`. The floor is what protects new branches.

### 6.3 Families

Descriptive only. Nothing is keyed to cluster identity, so families are recomputed every cycle, and should be: new branches open and the family structure is meant to move with them.

- **Cluster on the embeddings**, or on a PCA reduction of them. Hierarchical, with a cut chosen per cycle.
- **UMAP is for layout only.** Clustering on UMAP coordinates is known to manufacture structure, since the algorithm exaggerates local separation by design.
- Hierarchical rather than HDBSCAN, for two reasons. The dendrogram gives families at several granularities from one fit, so the analyzing LLM can read coarse families and then sub-families within one. And HDBSCAN's noise class would dump the least typical points into a catch-all, which is the opposite of what this search wants.
- Cluster ids are per-cycle and not stable across cycles. Nothing may depend on them persisting. Store `cluster.id` with the cycle it came from, plus `cluster.path`, the dendrogram path, which lets the viewer and the analyzing LLM move between granularities.

### 6.4 Deduplication

The dedup threshold is the most consequential single number in the system. Too tight keeps thousands of rephrasings; too loose merges away a genuinely new idea that shares vocabulary with an old one.

- Embed the **essence**, not the body.
- Calibrate the threshold against 50 pairs labelled by hand as same or different. Do this before any large run.
- **Bias loose.** A surviving duplicate costs one judge call. A bad merge costs the idea.
- On merge, log which operators and which arms converged. Convergence from different operators is a quality signal, not waste.

## 7. Evaluation

### 7.1 Tiers

A full panel on thousands of ideas is impossible, so almost everything dies to mechanical checks before any judge sees it.

| Tier | Applies to | Cost | Produces |
| --- | --- | --- | --- |
| 0. Schema and mechanical | Every idea | Script only | Valid or rejected; verified quotes and recomputed arithmetic |
| 1. Embedding | Every valid idea | Local model | Essence and body embeddings, baseline-cloud distance, duplicate flag |
| 2. Screening judge | Every non-duplicate | One cheap call | Provisional axis scores |
| 3. Full panel | Pareto front, each family's axis leaders and best `combined`, anything near the cull line | ~10 calls | Full reader vector, final axis scores |
| 4. Pairwise tournament | Top ~15 per arm per project | N log N paired calls | Bradley-Terry ranking |

Shape for a 7500-idea run: everything hits tiers 0 and 1, roughly 5000 reach tier 2, 300 to 400 reach tier 3, 30 reach tier 4. Counts are project config.

**Calibrate tier 2 against tier 3.** Periodically send a random sample of tier-2-only ideas through the full panel and measure rank correlation. Below about 0.6, the screening judge is deciding the run and its prompt needs work.

### 7.2 Mechanical verification

Before any scoring reader sees a packet:

- Every quote must appear verbatim in the source file. Non-matching quotes are stripped and the claims resting on them are void.
- Every arithmetic claim is recomputed. Failures are recorded as verified errors.

Highest-confidence and cheapest component in the system. It runs on every packet in every arm.

Decide before the first run whether to normalize quote characters and whitespace once at ingest, applying the same normalization to both source and candidate quotes. That is more robust than hoping the model reproduces typography exactly, and changing it later invalidates every earlier verification.

### 7.3 The reader panel

Each reader has a distinct job and produces a checkable artifact. Varying the scaffold around one identical scoring task leaves errors correlated; distinct jobs do not.

Evidence-producing readers run first. Scoring readers run second and receive the verified evidence. **No reader sees another reader's score.**

The reader list is domain config. Appendix A section 3 gives the critique pack's ten.

**Store the vector, never a collapsed number.** An idea at 0.2 on one reader and 0.9 on another is a different object from one at 0.55 on both.

### 7.4 Aggregation

Per lens, by a rule that fits the lens. Never a flat mean across everything.

| Lens type | Rule |
| --- | --- |
| Concession or error found | Any verified find wins |
| Correctness | Worst verified error wins |
| Strength | What survives the best objection anyone found |
| Insight, interest | Max across readers who produced supporting evidence |
| Clarity, dead weight | Mean |

**Selection uses the max across readers. Consensus is only for the final ranking.** One reader seeing something is enough to keep an idea alive. Averaging lets the strictest reader veto everything.

### 7.5 The judge

Combines the panel into the axis scores. It sees evidence first and scores second, because panel scores anchor it.

1. Score from the evidence alone and name the single decisive piece.
2. Then read the panel's scores. Any gap over 0.3 must be justified by citing evidence, or the figure changes. No splitting the difference without a reason.

Packet length is capped and the schema fixed, or the judge rewards confident, wordy packets.

**Escalation.** When evidence readers and scoring readers disagree by more than 0.4 on a shared dimension, route to a second independent judging with the panel outputs withheld. Log every escalation; the rate is a diagnostic.

### 7.6 Pairwise for the top

Absolute scores are for culling. The final ranking comes from a tournament.

Every pair runs twice with positions swapped. Position bias in pairwise judging is worst when the quality gap is small, which is exactly the condition in a top-15 tournament, so one ordering is not enough. Disagreement between orderings counts as a tie. Fit Bradley-Terry on the results.

### 7.7 Judge bias, given one model family

The published finding that judge panels beat a single judge concerns panels of **different model families**. This project has one, so role-differentiated readers do not buy what that result offers. Say so in the code comments and claim nothing stronger in any write-up.

Classic self-preference bias does not apply: it needs candidates from different models, and every candidate is Claude-generated. The live risk is different. The judge's sense of what a good idea looks like comes from the same training as the generator's, so an idea that is off-distribution in **form** can score low for being unfamiliar rather than wrong. That prunes exactly what the operators exist to find.

Four mitigations, none needing a second vendor:

1. **Split roles across capability tiers.** Evidence readers on the cheaper model, interpretive readers and the judge on the stronger one. This is the only model diversity available.
2. **Ground as much of the score as possible in verifiable evidence.** Quote matching and recomputed arithmetic are unaffected by how unfamiliar an idea is.
3. **A strangeness lens.** One reader answers whether a low-scoring idea is wrong, unclear, or unfamiliar in form, picking exactly one with a reason. Ideas marked `unfamiliar` get a floor on `off_distribution` (default 0.4) and are exempt from culling for three cycles. Revisit once lineage data shows whether `unfamiliar` ideas actually produce better descendants; if not, the floor is protecting noise.
4. **Escalation**, per 7.5.

The `off_distribution` axis is measured rather than judged, which keeps the axis most exposed to this bias out of the judge's hands entirely. The open-weights runs eventually give a genuine cross-family check at no API cost.

### 7.8 Winner's curse

Selecting the top from thousands of single-judged scores puts you several standard deviations into the noise distribution, and the top is enriched for ideas that drew a generous judge.

- **Shrink single-judged scores toward the pool mean** and select parents on the shrunken value. James-Stein style, factor estimated from tier-3 re-judging variance. Do not overbuild this.
- **Re-judge independently on promotion.** Anything reaching tier 3 is scored fresh, never by reusing the tier-2 figure.
- **The raw score is a filter, never a ranking.**

**Judge-drift check.** Hold out about 12 hand-rated anchors, never in the pool. Re-score them every few hundred ideas. If pool mean rises while anchor correlation falls, freeze the judge prompt: the search is optimizing the judge rather than the problem. The channel is real, since children see their parents.

## 8. Selection and operators

### 8.1 Selection

Parents are drawn by softmax over the drawing arm's weighted `combined`, with two guarantees:

- **Every family gets at least one expansion per cycle**, evaluated against the current clustering. A family that appeared this cycle is expanded this cycle.
- **A reserved share of draws is uniform at random across the whole live pool**, ignoring score entirely. Default 25%.

### 8.2 The operator registry

Operators come from the Conceptual Exploration Field Manual (CEFM). The registry holds **all of them**, not a subset. They are data: adding one is a YAML entry, and which ones a given run draws from is project config, never a design decision.

`operators/registry.yaml`, one entry per operator:

```yaml
- id: ceo-l1-01
  name: Inversion of Core Assumptions
  layer: L1                     # L1 Logical .. L7 Meta
  scope: [problem, parent]      # see 8.3
  arm_affinity: [insight]       # advisory only; both arms may draw any operator
  prompt: |
    <the CEFM prompt, verbatim>
  when_to_use: |
    <the CEFM "When to Use" text, verbatim>
  preconditions:                # machine-checkable version of when_to_use; see 8.4
    - "parent.generation >= 2"
    - "family.size >= 4"
```

`prompt` and `when_to_use` are copied verbatim from the manual. Ids are stable across the manual's rewrite into standard terminology; names and prompts may change under them.

**Three things to resolve in the manual rewrite, flagged because they affect the registry:**

1. The manual says twenty-six operators in one place and twenty-five in another, and the table lists twenty-seven entries.
2. Catastrophic Grace appears twice, as L4-04 and L5-03, with near-identical prompts. Either merge them or differentiate what the contextual version does that the dynamic one does not.
3. Several operators are written to act on a system or a research process, not on a single idea. Section 8.3 classifies them rather than dropping them.

### 8.3 Operator scope

Not every operator produces one child from one parent. The registry marks each with the scopes it supports, and the scheduler dispatches accordingly.

| Scope | Input | Output | Examples |
| --- | --- | --- | --- |
| `problem` | The problem file alone | One root idea | Inversion, Frame Collision, Anti-Pattern Design |
| `parent` | One parent idea | One child | Latent Role Mutation, Mirror Refraction, Minimal Intervention |
| `pair` | Two parents | One child | Frame Collision, Discordant Harmonization, Negative Capability |
| `pool` | A family, or the whole pool | An analysis, filed as an idea with `kind: analysis` | Symbolic Drift Mapping, Recursive Scaffold Echoes |
| `meta` | The run itself | A change to the schedule | The three L7 operators, section 8.7 |

**`pool`-scope operators are the ones I would otherwise have dropped, and they are worth keeping.** Symbolic Drift Mapping tracks how a term or motif mutates across a population, which is exactly the analysis an LLM should run over a family. Recursive Scaffold Echoes finds a structure repeating across layers, which over a pool means finding the same move recurring in ideas that look unrelated. Their outputs are not critiques; they are observations about the search, filed as ideas with `kind: analysis` so they are visible in the viewer, usable as collision parents, and excluded from the final export.

A domain pack may mark an operator unsupported if its scope makes no sense there. It may not rewrite the operator's prompt; that belongs in the registry.

### 8.4 When to use: hypotheses, not gates

Every CEFM operator carries a "When to Use" section. The tempting move is to turn those into eligibility rules so an operator is only drawn when its stated condition holds. That would be a mistake, and it breaks the measurement the project exists to make.

If eligibility is gated by the stated condition, and statistics only come from draws that happened, then the data can never contradict the condition. Discord Injection restricted to stagnant families can never be observed working on strong, developed ideas. The manual's own entry for it names testing resilience and reorganization capacity, which is something done to a developed idea, so gating it that way would rule out a use the manual itself describes.

So: **try everything equally, then see how it does.**

**The only hard gate is scope.** A `pair` operator needs two parents; a `parent` operator needs one; a `pool` operator needs a family. These are structural and cannot be otherwise. Everything else is open.

**`when_to_use` is recorded as a testable hypothesis**, not a filter:

```yaml
- id: ceo-l1-03
  name: Discord Injection
  when_to_use: |
    <verbatim CEFM text>
  hypothesis:                       # checkable expression; NOT used to restrict the draw
    - "family.mean_combined_delta < 0.02 over 3 cycles"
    - "parent.combined > 0.6"       # the resilience-testing use, from the same entry
```

An operator may carry several hypotheses, since the manual often names several conditions. Each is evaluated and logged at every application, whether or not it holds.

**Every application logs a state vector**, so lift can later be conditioned on context:

| Feature | Why |
| --- | --- |
| `parent.generation`, `parent.combined`, `parent.fitness.*` | Does the operator work better on weak or strong parents, early or late |
| `family.size`, `family.age`, `family.mean_combined_delta` | The stagnation conditions the manual names |
| `pool.family_count`, and its trend | Diversity state |
| `cycle.phase` (divergence, transition, synthesis) | The manual's Appendix D phases |
| `lineage.operators_used` | Whether an operator works better after certain others |
| `hypotheses_held` | Which of the operator's stated conditions were true at the time |

**Then fit lift as a function of operator and state.** Two results fall out, and both are worth having:

1. **Per operator: does the manual's stated condition predict its lift?** Report measured lift when the stated condition held against lift when it did not. A condition that shows no difference is either wrong or too vague to act on. A condition that shows a large difference is validated, and that validation is a real finding about the framework rather than an assumption baked into the code.
2. **Which state features predict lift better than the stated condition does?** This can find uses the manual does not name, which is the more interesting direction. An operator whose lift is predicted by parent strength rather than by family stagnation is telling you something the prose did not.

**Only after that** does the scheduler condition on context, and when it does it uses the **learned** relationship, not the stated one. Until there are enough samples, choice among scope-valid operators is uniform at random, which is also what keeps the lift estimates unbiased (section 8.6).

A practical note on sample size: conditioning lift on six state features across two dozen operators needs far more data than a marginal estimate. Start by testing only the stated hypotheses, which is a single binary split per operator and needs perhaps 30 to 50 applications on each side. Feature-level modelling waits until the pool is in the thousands.

### 8.5 Chains

The manual's Appendix C defines operator chains: ordered sequences with transition criteria, such as Inversion into Discord Injection into Harmonization. A chain is not the same as applying three operators separately, because each step acts on the previous step's output within one reasoning pass.

Chains are first-class. `operators/chains.yaml`:

```yaml
- id: cefm-c1
  name: Exploratory Divergence
  sequence: [ceo-l1-01, ceo-l1-03, ceo-l3-01, ceo-l2-01]
  stop_when: "coherence_loss > 0.4"     # the manual's own criterion
  arm_affinity: [insight]
```

A chain is dispatched as one subagent call with the full sequence in its prompt, each step labelled, and the subagent instructed to carry its own output forward between steps and to stop early if the stop criterion is met, saying which step it stopped at. The resulting idea records `origin: chain:<id>` and `chain_stopped_at`.

Chains get their own statistics, identical to single-operator statistics, plus the distribution of stopping points. A chain that always stops at step two is telling you something about steps three and four.

Start with all six of the manual's templates. C.5 (Iterative Meta-Exploration) is a meta chain and belongs in section 8.7, not here.

### 8.6 Operator statistics

This is the manual's Meta-Reflection operator (L7-03) made automatic. Track, per operator and per chain, per arm, and per depth bucket. Track the same statistics per **seeding strategy**, where the relevant lift is the lift of a seed's children rather than the seed's own score: a strategy that produces mediocre ideas which operators improve is a good strategy.

| Statistic | Definition |
| --- | --- |
| Hit rate | Share of children above a threshold on `combined` |
| Mean lift | Mean of (child `combined` minus parent `combined`) |
| P90 lift | 90th percentile of lift. Where a noisy but occasionally excellent operator shows up |
| Per-axis lift | Mean lift on each axis separately. An operator can raise one and lower another |
| Pareto entry rate | Children entering the Pareto front, per attempt |
| New-family rate | Children forming a family containing no earlier idea, per attempt |
| Duplicate rate | Children merged as duplicates |
| Cross-arm yield | Children that migrated, per attempt |
| Lift when stated condition held | Mean lift on applications where a `hypothesis` was true, against applications where it was false. This is the test of the manual's "When to Use" |
| Stop distribution | For chains: which step it stopped at |

**Never collapse these into one number.** An operator with low mean and high P90 is a valuable operator, and the manual's own framing anticipates this: some operators are expected to produce noise most of the time and an excellent direction occasionally.

**Unbiased estimation.** If operator choice depends on past performance and parents are chosen by score, an operator that drew good parents looks good. Reserve 25% of generations for uniform random assignment among the eligible set. Only those runs feed the statistics.

The manual's Appendix D metrics (Novelty Ratio, Coherence Entropy, Resonance Index, Conceptual Survival Rate, Exploration Efficiency, Meta-Adaptive Gain) map onto quantities the system already computes. Implement them under the manual's names so runs are comparable with manual-mode work:

| CEFM metric | Computed as |
| --- | --- |
| Novelty Ratio | 1 minus cosine similarity between a new idea's body embedding and the pool centroid |
| Coherence Entropy | Entropy of `correctness` and `clarity` across a cycle's children |
| Resonance Index | Mean pairwise similarity among ideas surviving culling |
| Conceptual Survival Rate | Share of ideas still live after two or more operator applications in their lineage |
| Exploration Efficiency | Ideas reaching tier 3 per 1000 tokens |
| Meta-Adaptive Gain | Change in Exploration Efficiency or Novelty Ratio between epochs |

### 8.7 The three meta operators

These are not generation operators and must not be in the generation draw. Each maps onto part of the search controller.

**Discordant Colony Iteration (L7-01).** Run several operators on the same parent in one cycle and study the cross-effects. Implemented as a dispatch mode: with probability `colony_share` (default 0.1), a selected parent is expanded by `k` different eligible operators simultaneously rather than one. The children are tagged with a shared `colony_id`. What this buys that separate draws do not: a controlled comparison of operators on an identical parent, which is a much cleaner lift estimate than the population-level one. Prioritize colony draws for operators with few random-assignment samples.

**Operator Chain Governance (L7-02).** The scheduler itself. It sets, per cycle: the eligible set, the single-versus-chain-versus-colony mix, the collision share, and when to trigger a fresh-start epoch. The manual's criterion is to balance novelty against coherence and to adjust as insight density changes. Concretely: if Novelty Ratio falls below its target band for the current phase (the manual's Appendix D gives bands per phase), raise the random reserve and shift the mix toward whichever operators have measured high new-family rates. If Coherence Entropy rises above its band, shift toward operators with measured high refine-like lift. Thresholds live in `project.yaml` and start at the manual's published values.

Note what this does not do: it never shifts the mix on the basis of the manual's layer taxonomy or stated conditions, only on measured behavior. Whether the layers predict anything is one of the results the run produces (section 9.1), so it cannot also be an input to the scheduler. Governance stays off until section 8.4's estimates exist.

**Meta-Reflection (L7-03).** Section 8.6, plus an explicit pass at the end of each epoch: an LLM call that reads the epoch's operator statistics and the pool-scope analyses and writes what moved and what stagnated, filed as an idea with `kind: analysis`. This is the manual's own instruction and it produces a human-readable run narrative that the statistics tables do not.

### 8.8 Refine

One operator not in the manual, added because every CEFM operator perturbs and none polishes. Input: one idea plus the adversary's best objection to it. Output: a rewrite that survives the objection, keeping the same target. It is where a 0.45 becomes a 0.65, and it gives the gradient something continuous to descend rather than only discrete jumps. Expect it to dominate late cycles, and expect Operator Chain Governance to shift toward it as Coherence Entropy rises.

Its statistics are tracked like any other operator's. If it does not earn its share, the scheduler will stop drawing it.

## 9. Arms

### 9.1 The two operator arms

| | Insight arm | Rational arm |
| --- | --- | --- |
| Question | Does this reveal something about the space? | Does this do the job? |
| Weights | `off_distribution` high | `task_fitness` high |
| Generator | Creative prompt | Analytic prompt |
| Operator affinity | L1 Logical, L3 Interpretive, L6 Dialectical | L2 Structural, L4 Dynamic, L5 Contextual |

`arm_affinity` in the registry is advisory. Both arms may draw any eligible operator, and the statistics learn the split. An early lopsided split is expected and is itself a result: it is a measurement of the manual's layer taxonomy, not an assumption built into the code.

**Migration.** An idea moves arms when its `combined` under the other arm's weighting exceeds its `combined` under its home weighting by a margin (default 0.15), measured after shrinkage; or when a cross-arm collision produces a child outscoring both parents under the destination arm's weighting. A migrated idea keeps its id, lineage and history, and gains a `migrations` entry.

Migration rate is a diagnostic. Near zero means the arms have drifted apart and the exchange is not happening. Above about 25% per cycle means they are not differentiated.

### 9.2 Cross-arm collisions

One insight parent, one rational parent, both clearing a floor on their home fitness. The prompt asks what the insight parent's picture does to the rational parent's fact, or the reverse.

This is the pairing that produced the best result in the by-hand run: a picture that scored near zero on task fitness, crossed with a fact that had been read as supporting the argument. It gets a reserved share of the collision budget rather than competing for it. Default: half of all collisions.

### 9.3 The baseline arm

Both the control condition and the reference cloud for `off_distribution`, which is why it runs early.

- Repeated independent sampling from the problem brief alone.
- No operators, no parents, no pool feedback, no frames.
- Same dedup threshold, same tiers 0 to 2, same embedding model.

Published measurements of naive repeated LLM ideation report roughly half of the first 500 samples being non-repetitive, then sharp diminishing returns, down to about an eighth in the fourth thousand. That is the curve the operator arms must beat, and without running it on this problem there is no local version of it.

**Primary cross-arm metric: distinct families discovered per 1000 tokens spent.** Report the curve, not a number. Since family ids are not stable across cycles, compute this at the end by clustering all arms together once in a common space and counting families each arm reached.

Secondary: best `task_fitness`, mean of the top decile, Pareto front size, share of top ideas whose lineage includes a human seed.

Budget about 5% of the run. If the naive arm matches the operator arms on family coverage, that is a real finding and worth knowing before the rest is built on top.

## 10. Lineage and diagnostics

### 10.1 Lineage credit

An idea's value as a parent is measurable through its descendants, which turns "was this generative?" into a statistic.

```
lineage_value(idea) += decay^depth * max(0, descendant.combined - idea.combined)
decay = 0.6
```

Recomputed on each tier-3 scoring. Cheap, since lineages are short. It is also the ground truth for which reader's verdict predicts eventual quality: track, per reader, the correlation between that reader's score and the idea's eventual lineage value.

### 10.2 Diagnostics, logged every cycle

| Metric | Why |
| --- | --- |
| Family count and sizes | Collapse detection. Falling family count while the pool grows means selection is collapsing and the random reserve needs raising |
| Pairwise axis correlation, pool-wide | Do the axes conflict globally? |
| Pairwise axis correlation, within each cluster | Clusters where conflicting axes correlate positively are where the interesting search is happening. A finding about the space, not about an idea |
| Pareto front size and composition | Front shape over time |
| Migration rate | Arm differentiation |
| Interpolation score for collision children | Section 10.3 |
| Escalation rate | Judge disagreement |

### 10.3 Interpolation score

For a child of a cross-arm or cross-family collision, compute cosine similarity in **embedding space**, not UMAP coordinates, to each parent's family centroid. A child similar to both, and closer to each than the parents are to each other, is genuinely interpolating. A child close to one parent only has collapsed onto a side.

This answers directly whether the collision operator produces hybrids or just picks a winner.

## 11. Data model

One JSON object per idea. The core schema is fixed; the domain pack fills `fields` and `readers`.

```json
{
  "id": "uuid",
  "project": "example-project",
  "arm": "insight | rational | baseline",
  "frame": "none | <frame-id>",
  "parents": [],
  "origin": "root | operator:<id> | chain:<id> | collision | cross-collision | refine",
  "strategy": "human | direct | step-targeted | assumption-first | adversary-role | frame-seeded | deliberate | null",
  "cycle": 0,
  "generation": 0,

  "body": "The idea, within the domain's word limit.",
  "translation": "Present when the frame requires it.",
  "fields": {},
  "essence": "Neutral one-sentence restatement, used for embedding and dedup.",

  "evidence": {
    "quotes": [{"text": "", "verified": true, "source_offset": 0}],
    "computations": [{"claim": "", "recomputed": "", "passed": true}],
    "adversary": "",
    "defense": "",
    "repair": {"description": "", "cost": 0.0}
  },
  "readers": {},

  "fitness": {"off_distribution": 0.0, "task_fitness": 0.0},
  "fitness_detail": {
    "baseline_distance": 0.0,
    "token_surprisal": 0.0,
    "off_distribution_source": "baseline_cloud | pool_centroid"
  },
  "combined": 0.0,
  "shrunk_combined": 0.0,
  "pareto_front": false,
  "lineage_value": 0.0,
  "tier": 0,
  "kind": "domain-declared",

  "cluster": {"cycle": 0, "id": 7, "path": "root/3/7"},
  "retained_by": "pareto | axis:<name> | combined | random | none",
  "status": "live | archived | merged",
  "merged_into": "",
  "convergence_count": 0,
  "answers": "",
  "migrations": [{"cycle": 0, "from": "insight", "to": "rational", "reason": ""}],

  "strangeness": {"verdict": "wrong | unclear | unfamiliar | none", "reason": ""},
  "interpolation": {"parent_similarity": [0.0, 0.0], "parent_distance": 0.0, "score": 0.0},
  "escalated": false,
  "trace_ids": ["call-id"]
}
```

Storage: append-only `pool/ideas.jsonl`, `pool/runs.jsonl`, `pool/operators.jsonl`. SQLite is fine if a JSON export exists for the viewer.

`answers` links an objection or defense to the idea it responds to.

## 12. Trace logging

**Log every model call verbatim** to `traces/<cycle>/<call-id>.json`, from the very first call:

```json
{
  "call_id": "uuid",
  "cycle": 0,
  "role": "generator | collider | judge | reader:<name>",
  "model": "",
  "params": {"temperature": 1.0, "effort": "high"},
  "system_prompt": "verbatim, in full",
  "messages": [],
  "completion": "verbatim, in full",
  "prompt_hash": "",
  "idea_id": "uuid",
  "operator": "operator-id-or-null",
  "parents": [],
  "arm": "",
  "tokens": {"input": 0, "output": 0},
  "timestamp": ""
}
```

No summaries, no truncation. Storage is trivial next to the value and none of it is recoverable later.

What it enables: replay any prompt through a local model and capture residual-stream trajectories per operator. The question that falls out is whether different operators produce measurably different internal trajectories, or whether the variation is only in output text. Either answer is a result.

Two cheap things to build alongside:

- **A replay script.** Takes a trace file, re-runs the call against a configured endpoint (local or API), writes results beside the original. This is how the open-weights arm runs without reimplementing the pipeline, and how token surprisal gets computed.
- **A stable prompt hash.** Hash the system prompt plus operator id. Comparing trajectories requires grouping by exactly-identical prompt, and the hash makes that an index lookup.

## 13. The viewer

Both arms share one embedding space so the cross-feeding is visible; side-by-side plots would hide the thing most worth seeing.

- Embeddings: local sentence-transformers.
- Projection: UMAP to 3D, with 2D and PCA as toggles. UMAP distorts global distance, so the PCA toggle is the check on any structure UMAP appears to show.
- One standalone `viz/index.html` using Plotly, reading `viz/data.json`, rebuilt by a script after each batch. No server.

Controls:

- Color by arm (default), either axis, `combined`, family, generation, origin, operator, or Pareto membership.
- Size by whichever axis is not driving color, so disagreement between axes is visible at a glance.
- Edges on toggles: lineage, collisions, cross-arm collisions, migrations.
- Filter by status, tier, kind, family.
- Cycle slider replays growth.
- Click a node for body, essence, full reader vector, evidence with verification marks, adversary and defense, lineage path, cluster path, migration history.

If the two arms do not separate visually, that is a finding: either the generator prompts are not differentiated enough, or the embedding is dominated by problem vocabulary rather than by approach. Check the second by embedding with the problem's most frequent terms removed.

## 14. Claude Code setup

Subagent definitions are Markdown files with YAML frontmatter in `.claude/agents/`. Only `name` and `description` are required. The definitions are generic and never name a domain.

```markdown
---
name: idea-generator
description: Writes one idea from the files named in its task message. Use only when the cycle runbook dispatches it.
tools: Read, Write
model: sonnet
omitClaudeMd: true
---
Your task message lists file paths: generator prompt, problem, optional frame,
optional operator, optional parent, and an output path.
Read them. Follow the generator prompt exactly.
Write one JSON object to the output path. Reply with that path only.
```

```markdown
---
name: idea-judge
description: Combines a panel's evidence into scores for one idea. Use only when the cycle runbook dispatches it.
tools: Read, Write
model: claude-opus-5
effort: high
omitClaudeMd: true
---
Your task message lists file paths: judge prompt, problem, idea, evidence packet,
and an output path.
Read them. Follow the judge prompt exactly, step by step, without looking ahead.
Write the judgment JSON to the output path. Reply with that path only.
```

`idea-collider` and `idea-reader` follow the same pattern.

Notes: generators can run on Sonnet or Haiku for breadth; models per role are set in `project.yaml`. The default limit is 20 concurrent subagents; expect 3 to 5 at a time. Define one repeatable entry point for a cycle, checking the current docs for the right mechanism.

## 15. Repo layout

```
idea-evolver/
  CLAUDE.md                 orchestrator rules only, no idea content
  docs/brief.md             this file
  core/                     evolve.py, embed.py, verify.py, cluster.py, viz.py, replay.py
  operators/registry.yaml
  domains/<domain>/
    domain.yaml
    lenses.yaml
    prompts/
  projects/<project>/
    project.yaml
    problem.md
    sources/                verbatim source texts
    frames/  seeds/  anchors/
    dispatch/  inbox/  pool/  traces/  viz/  export/
  .claude/agents/           idea-generator.md, idea-collider.md, idea-reader.md, idea-judge.md
```

## 16. Build order

1. Skeleton, core schema, the critique domain pack from Appendix A. Operator registry with all CEFM operators transcribed verbatim, their scopes assigned, and their `when_to_use` transcribed and translated into checkable hypotheses by hand (recorded, not enforced). Chains from CEFM Appendix C. This transcription is a real task, not boilerplate.
2. **Trace logging from the very first call.** Plus the prompt hash and the replay script stub.
3. One generator subagent, inbox, ingest. Five roots on one project. Measure tokens per call.
4. Tier 0 and 1: schema validation, mechanical verification, embeddings, dedup threshold calibrated on 50 hand-labelled pairs.
5. Seeding strategies (section 4.1), including human seeds. The `direct` strategy at scale is the baseline arm: it gives the local saturation curve and the reference cloud.
6. `off_distribution` by baseline-cloud distance; token surprisal once replay runs.
7. Round 1: exhaustive operator expansion over all seeds, tiers 0 and 1 only.
8. Draw about twelve anchors from round-1 output, rate them blind by hand, then build and calibrate the tier 2 screening judge against them.
9. Fitness vector, geometric-mean combination, Pareto front.
10. Families, cluster-stratified culling with quotas and floor.
11. Both operator arms, migration rule. First full cycles. Log section 10.2 diagnostics from here.
12. Tier 3 reader panel, tier split across models, strangeness lens, escalation. Calibrate tier 2 against tier 3.
13. Operator statistics with the random-assignment reserve, CEFM Appendix D metrics, and the end-of-epoch Meta-Reflection pass. Shrinkage, Thompson sampling and lineage credit computed as fields but **not driving selection**.
14. Collisions including cross-arm, plus the interpolation score. Chains, colony draws, and pool-scope operators.
15. Operator Chain Governance: phase detection and the mix adjustments of section 8.7.
16. Switch on shrinkage, Thompson sampling and lineage credit once there are 30+ random-assignment samples per operator.
17. The viewer.
18. Tier 4 tournament and the review export.
19. A second domain pack, to prove the core carries it with no code change.

## 17. Token budget

Every knob lives in `project.yaml`: children per cycle, collision share, cross-arm share, fresh-start frequency, random reserve, tier counts, model per role.

Judge only what survives the cheap checks: schema validation, then embedding dedup, then the screening judge. Batch judging (several ideas per call, shuffled) is allowed if per-idea calls cost too much, but test whether batching changes scores before adopting it.

Milestone 3 measures real tokens per call. Set the per-cycle budget from those numbers.

## 18. Final export

`export/review-<project>.md`: the top N per arm, each with body, essence, evidence with verification marks, the adversary's objection and what survives, lineage path with parents' scores, and cluster path. Sorted by tournament rank.

A person picks from this and rewrites in their own words. The system produces candidates, never submissions.

## 19. What is most likely to go wrong

- **Dedup threshold set by feel.** The highest-leverage number and the easiest to get wrong. Calibrate before any large run.
- **Tier 2 deciding the run.** If the screening judge is miscalibrated, the panel never sees the good ideas. The tier-2-versus-tier-3 correlation check is the alarm.
- **Judge and generator sharing blind spots.** Ground as much of the score as possible in quotes and arithmetic; treat the judged axes as where drift appears first.
- **Arms collapsing into each other.** Watch migration rate and viewer separation.
- **Operator statistics contaminated by selection.** The random-assignment reserve is not optional.
- **Prejudging where an operator works.** Any rule that stops an operator being tried in some state also stops you learning it works there. Scope is the only legitimate gate. If a scheduling heuristic creeps in later, make sure the random reserve still samples uniformly across all scope-valid operators.
- **Saturation unnoticed.** Track distinct families per 100 accepted ideas. When it flattens, stop generating and spend the rest of the budget on refinement.

---

# Appendix A: the argument-critique domain pack

Everything here is domain-specific by design. Nothing in it may be imported by core code. If the core needs to know what a "step" is, the abstraction has leaked and the fix belongs in the core.

The fenced blocks are extracted to real files at the paths in their headings. Prompts are written out verbatim so they can be copied without paraphrase; rewording them changes the experiment.

## A.1 What this pack is for

The task these projects come from asks for a critique "focused on a single issue, aimed at refuting the argument as much as possible." An idea does well when an author reading it would have to give something up.

## A.2 `domains/argument-critique/domain.yaml`

```yaml
name: argument-critique
description: >
  Critiques of a written argument. An idea does well when it makes a numbered
  step false or unsupported, and when the author cannot repair it cheaply.

axes:
  - {name: off_distribution, measured: true}
  - {name: task_fitness, measured: false}

arm_weights:
  insight:   {off_distribution: 0.7, task_fitness: 0.3}
  rational:  {off_distribution: 0.3, task_fitness: 0.7}
  baseline:  {off_distribution: 0.5, task_fitness: 0.5}

kinds: [critique, implication, defense]
export_kinds: [critique]    # only these reach the review file;
                            # all kinds remain parents and remain in the pool

essence_form: >
  One sentence naming which step is threatened and why. Neutral phrasing, no
  hedging, no rhetorical framing. Two ideas with the same content must produce
  near-identical essences.

idea_fields:
  target_step: "The step id this attacks, from the project's step list."
  adversary_guess: "The generator's own guess at the author's best reply."

word_limit: 200

task_fitness:
  formula: "centrality * strength"
  strength_caps: {explicit: 1.00, implied: 0.75, none: 0.50}
  priced_in_cap: 0.50
  zero_when: "correctness < 0.5"

culling: {quota_rate: 0.3, quota_floor: 3, random_reserve: 0.25}
```

**Caps multiply; they do not take the minimum.** An idea that is `implied` and priced in caps at 0.375.

**The only zero** is `correctness < 0.5`, meaning the idea asserts something false. Nothing else zeroes a score. The worked example in A.7.1 exists to catch a regression on this.

## A.3 `domains/argument-critique/lenses.yaml`

```yaml
readers:
  - id: locator
    model: sonnet
    phase: evidence
    question: >
      Which numbered step does this idea make false or unsupported? Quote the
      sentence in the source that states that step. If the idea does not name a
      step, decide whether you can name one yourself from its content. If you
      can, write the sentence the idea is missing.
    output:
      verdict: {type: enum, values: [explicit, implied, none]}
      step: {type: string}
      quote: {type: string, must_appear_in: source}
      implied_statement: {type: string, required_when: "verdict == implied"}

  - id: concession_hunter
    model: sonnet
    phase: evidence
    question: >
      Does the source already concede this point, anywhere, including in its
      stated caveats and in sections it defers to later? Quote the conceding
      sentence. Do not stretch: conceding something adjacent is not conceding
      this.
    output:
      found: {type: bool}
      quote: {type: string, must_appear_in: source}
      scope: {type: enum, values: [full, partial, none]}

  - id: verifier
    model: sonnet
    phase: evidence
    question: >
      List every factual and numerical claim. For each, state whether it
      follows from the source. Recompute every arithmetic claim, showing work.
    output:
      claims: {type: list, fields: [claim, status, computation]}
      correctness: {type: score}

  - id: style_auditor
    model: sonnet
    phase: evidence
    question: >
      Label each sentence: on-target, supporting, or dead weight.
    output: {labels: {type: list}, dead_weight: {type: score}, clarity: {type: score}}

  - id: adversary
    model: opus
    phase: evidence
    question: >
      You are the author of the source. Write your best reply in three
      sentences or fewer. Use what the text already says where you can.
    output: {reply: {type: string}, quote: {type: string, must_appear_in: source, optional: true}}

  - id: defender
    model: opus
    phase: evidence
    question: "Answer the author's reply. What survives of the idea after it?"
    output: {answer: {type: string}, survives: {type: string}}

  - id: repair_tester
    model: opus
    phase: evidence
    question: >
      What is the cheapest change to the argument that would save it? State the
      change, then what the author loses: which claims weaken, which further
      premises are now needed.
    output: {repair: {type: string}, cost: {type: score}}

  - id: insight
    model: opus
    phase: scoring
    question: >
      Does this name a mechanism, actor, dependency or incentive the source
      leaves implicit? Quote what the source says about it, or state that it
      says nothing.
    output: {names_mechanism: {type: score}, what: {type: string}}

  - id: interest
    model: opus
    phase: scoring
    question: >
      Would an expert find this interesting, setting aside whether it lands a
      blow? Give one reason.
    output: {interest: {type: score}, reason: {type: string}}

  - id: strangeness
    model: opus
    phase: scoring
    question: >
      If this scores low, is it because it is wrong, because it is unclear, or
      because it is unfamiliar in form? Pick exactly one and say why. Answer
      "none" only if it does not score low.
    output: {verdict: {type: enum, values: [wrong, unclear, unfamiliar, none]}, reason: {type: string}}

aggregation:
  concession_found: any_verified
  correctness: min
  strength: from_defender_survives
  centrality: from_locator_and_judge
  clarity: mean
  dead_weight: mean
  names_mechanism: max_with_evidence
  interest: max_with_evidence
```

**`strength` comes from the defender, not from a direct score.** It is how much survives the author's best reply, cross-checked against the repair tester's cost. An idea the author neutralizes by quoting his own text has low strength no matter how well written. This is the operational meaning of "refuting as much as possible."

**`centrality` is how load-bearing the attacked step is**, not how important the idea feels. A step the conclusion cannot survive without scores near 1.

## A.4 Prompts

### `domains/argument-critique/prompts/generator-rational.md`

```
You will be given: a problem file containing an argument and its numbered
steps, optionally a frame file, optionally an operator, and optionally one
parent idea.

Write ONE critique of the argument.

A critique succeeds when the author, reading it, would have to give something
up: a premise, an inference, or the conclusion's strength. It fails when the
author can agree with every word and keep the argument intact.

Before writing, do this and do not skip it:
1. Pick the step you are attacking. Write its id.
2. Write the author's best reply to what you are about to say.
3. If that reply defeats you, pick a different step or a different attack.

Rules:
- One issue only. Not a survey of problems.
- Attack the argument as written. Do not attack a stronger or weaker version
  of it, and do not substitute a different subject matter for its terms unless
  a frame file tells you to.
- If the source already concedes your point, you have not found a critique.
  Quote the concession to yourself and start again, or go past what the
  concession covers and say exactly where you go past it.
- Every quote from the source must be verbatim. Quotes are checked
  mechanically and a wrong quote voids the claim it supports.
- Every number must be one you computed. Show the computation in the body if
  it is not obvious.
- Maximum 200 words in the body.

If you were given an operator, apply it. The operator tells you how to
perturb, not what to conclude. If the operator produces nothing that lands on
a step, say so in your body and write what it did produce; an honest
near-miss is more useful than a forced critique.

If you were given a parent idea, your job is to produce something different
from it, not a rewording of it. If you end up restating the parent, say so.

Output JSON to the path you were given:
{
  "body": "...",
  "target_step": "...",
  "adversary_guess": "...",
  "translation": "... or null"
}
Reply with the output path only.
```

### `domains/argument-critique/prompts/generator-insight.md`

```
You will be given: a problem file containing an argument and its numbered
steps, optionally a frame file, optionally an operator, and optionally one
parent idea.

Write ONE observation about the argument.

Your job is NOT to refute it. Your job is to notice something true about how
it works that the text does not make explicit: a mechanism it relies on, an
actor whose incentives it does not consider, a dependency between two of its
claims, a quantity it treats as given that something in the world controls.

Ideas from this prompt are judged on whether they open a direction, not on
whether they land a blow. An observation that names a real mechanism and
stops short is worth more here than a weak refutation.

Rules:
- One observation. Not a list.
- It must be about THIS argument, traceable to something the text says or
  assumes. Quote what the text says about the thing you are naming, or state
  plainly that it says nothing about it.
- Every quote must be verbatim; quotes are checked mechanically.
- Do not hedge into vagueness to seem safe. A specific claim that turns out
  wrong is more useful than a vague one that cannot be wrong.
- Maximum 200 words.

If you were given an operator, apply it. If you were given a parent, produce
something different from it.

If you can see which step your observation threatens, name it. If you cannot,
do not invent one; leaving it unnamed is a valid outcome for this prompt.

Output JSON to the path you were given:
{
  "body": "...",
  "target_step": "... or null",
  "adversary_guess": "...",
  "translation": "... or null"
}
Reply with the output path only.
```

### `domains/argument-critique/prompts/collider.md`

```
You will be given: a problem file, and TWO parent ideas, A and B.

Produce ONE new idea that uses both.

The target: use A to defeat the strongest objection to B, or use B to defeat
the strongest objection to A. If one parent is an observation about a
mechanism and the other is a fact about the argument's structure, the usual
productive move is to ask what that fact implies about that mechanism.

Do not:
- Write a summary of A and B.
- Write "A and B are both true" with a connective sentence.
- Pick one parent and restate it with a nod to the other.

If the two genuinely do not combine, say so in one sentence and write which of
them the other undermines, if either. That is a real result.

Rules from the generator prompts apply: one issue, verbatim quotes, computed
numbers, 200 words.

Output JSON to the path you were given:
{
  "body": "...",
  "target_step": "... or null",
  "adversary_guess": "...",
  "used_from_a": "one sentence: what A contributed",
  "used_from_b": "one sentence: what B contributed"
}
Reply with the output path only.
```

### `domains/argument-critique/prompts/refine.md`

```
You will be given: a problem file, ONE parent idea, and the author's best
reply to it.

Rewrite the idea so that it survives the reply. Keep the same target step.

You may: add a premise, narrow the claim, block the reply's escape route,
replace a weak sub-argument, supply a computation the original asserted.

You may not: change which step is attacked, broaden into a second issue, or
answer the reply by asserting it is wrong without saying why.

If the reply cannot be survived without changing the target step, say so in
one sentence. That is a real result about the idea and it stops the search
wasting further effort on it.

Rules from the generator prompts apply.

Output JSON to the path you were given:
{
  "body": "...",
  "target_step": "...",
  "adversary_guess": "...",
  "what_changed": "one sentence"
}
Reply with the output path only.
```

### `domains/argument-critique/prompts/judge.md`

```
You will be given: the problem file, one idea, and the panel's evidence with
each quote marked verified or unverified. Unverified quotes have been
stripped and the claims resting on them are void.

Work in this order and do not look ahead.

STEP 1. From the evidence alone, before you see any panel score:
  a. Name the single most decisive piece of evidence and say what it decides.
  b. Assign centrality (0 to 1): how load-bearing is the attacked step? A step
     the conclusion cannot survive without is near 1. A step that could be
     dropped with the conclusion intact is near 0. Use the locator's quote.
  c. Assign raw strength (0 to 1): how much survives the author's best reply,
     per the defender, cross-checked against the repair tester's cost. An idea
     the author neutralizes by quoting his own text is near 0. An idea whose
     cheapest repair costs the author his conclusion is near 1.
  d. Assign correctness (0 to 1) from the verifier's per-claim findings. Any
     verified false claim caps this below 0.5.
  e. Set kind: critique if a step is named or implied; implication if the idea
     is true and interesting but threatens no step; defense if it supports the
     argument.

STEP 2. Apply the caps:
  strength = raw_strength * locator_cap * priced_in_cap
  locator_cap: explicit 1.00, implied 0.75, none 0.50
  priced_in_cap: 0.50 if the concession hunter found a verified full
                 concession, else 1.00
  task_fitness = centrality * strength
  task_fitness = 0 ONLY IF correctness < 0.5

STEP 3. Now read the panel's scores. For any dimension where you differ from
the panel aggregate by more than 0.3, either cite the evidence that justifies
your figure, or change your figure. Do not split the difference without a
reason.

STEP 4. Write the essence: one neutral sentence naming which step is
threatened and why. This string is used for deduplication, so two ideas with
the same content must produce near-identical essences. No hedging, no
rhetorical framing, no reference to the idea's author or quality.

Output JSON to the path you were given, with every field above, plus a
one-sentence justification for centrality and for strength.
Reply with the output path only.
```

### `domains/argument-critique/prompts/pairwise.md`

```
You will be given: the problem file and TWO ideas, X and Y, each with its
evidence packet.

One question: which one would cost the author more to answer?

Not which is better written, not which is more interesting, not which is more
original. Which forces a bigger concession.

Consider: whether the attacked step is more load-bearing; whether the cheapest
repair is more expensive; whether the author can answer one by quoting himself
and not the other.

Answer with the winner and one sentence of reasoning naming the deciding
factor. If they are genuinely equal, say so; do not break a tie for the sake
of it.

Output JSON: {"winner": "X | Y | tie", "reason": "..."}
Reply with the output path only.
```

## A.5 Frames

*Withheld from the public copy.* This part used example problems that are not published. A new example is planned to replace them.

## A.6 Projects

*Withheld from the public copy.* This part used example problems that are not published. A new example is planned to replace them.

### `projects/*/project.yaml`

```yaml
domain: argument-critique
source: sources/problem.txt
arms: [insight, rational, baseline]
frames: [<frame-id>]
models:
  generator: sonnet
  collider: sonnet
  evidence_readers: sonnet
  interpretive_readers: claude-opus-5
  judge: claude-opus-5
  screening_judge: sonnet
budget:
  children_per_cycle: 24
  collision_share: 0.15
  cross_arm_collision_share: 0.5
  fresh_start_every: 8
  random_operator_reserve: 0.25
```

### Source files

`sources/problem.txt` holds each argument text verbatim, exactly as published, with no reformatting and no fixed typos. The verifier and concession hunter match quotes by exact string against them, so a smart quote or a normalized whitespace run will fail a quote that is actually correct. Paste them raw and leave them alone. See section 7.2 on the normalization decision.

## A.7 Anchors

Anchors are not written in advance. They are drawn from round-1 output and rated by hand, per section 4.1. Twelve is enough.

When picking the twelve, aim to cover the three ways a score goes wrong, because those are what the calibration is for:

- At least one idea that identifies a real mechanism without formalizing an attack. Tests that `implied` caps rather than zeroes.
- At least one idea that is correct and central but already conceded by the source. Tests priced-in detection.
- At least one idea that asserts something false. Tests that this is the only route to zero.

If round 1 produces none of a category, write one by hand for that slot and mark it synthetic. A synthetic anchor is fine for calibration; it is not fine as a seed, so keep it out of the pool.

Rate blind: strip strategy, operator, arm and lineage, and shuffle. Keep your own seeds out of the anchor set, so that the later comparison between your seeds and the evolved population stays independent of the judge you calibrated.

## A.8 Worked examples: cap arithmetic

*Withheld from the public copy.* This part used example problems that are not published. A new example is planned to replace them.

## A.9 Sanity checks for the first run

Not success criteria.

- The baseline arm should produce a tight cloud with several near-duplicates in the first hundred. If not, the dedup threshold is too tight.
- The insight arm should produce a visibly higher share of `none` and `implied` locator verdicts than the rational arm. If the arms look the same, the generator prompts are not differentiated and everything downstream is measuring noise.
- The priced-in rate should be highest in the baseline arm. The default critiques of a text are usually the ones its author anticipated.
- The three cap cases of A.8 compute correctly every time the judge prompt changes.

---

# Appendix B: sketches of two more packs

Starting points, to be tuned. They exist to show the core carries other kinds of ideas.

## B.1 `game-design`

Essence form: "The player does X and the system responds with Y."

Axes: `off_distribution`, `task_fitness`.

| Lens | Question | Output |
| --- | --- | --- |
| `fits_constraints` | Does it fit the platform, scope and genre in the brief? Name any constraint it breaks. | Bool plus text |
| `core_loop` | What does the player do minute to minute? | Text. If none, `kind: theme` |
| `precedent` | Closest existing game or mechanic, and how this differs. | Text |
| `adversary` | The strongest reason it will not be fun or will not ship, then what survives. | Text |
| `novelty`, `depth`, `fantasy_clarity`, `feasibility` | Depth means interactions with the game's other systems. | Scores |

`task_fitness` = `depth * feasibility`, capped when `fits_constraints` is false. No categorical structure, so no locator lens and no caps table.

## B.2 `problem-solving`

Essence form: "Do X in order to get Y."

| Lens | Question | Output |
| --- | --- | --- |
| `addresses_problem` | Which part of the stated problem does this solve? | Text. If none, `kind: tangent` |
| `assumptions` | What must be true for this to work? | Text |
| `cheapest_test` | The smallest experiment that would show it fails. | Text |
| `adversary` | The most likely failure mode, then what survives. | Text |
| `impact`, `feasibility`, `cost`, `risk` | Judged against the brief's constraints. | Scores |

`task_fitness` = `impact * feasibility`, reduced by `risk`. Capped when a hard constraint is broken.