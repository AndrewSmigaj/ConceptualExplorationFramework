# Technique invention: design pass 1

**Status: for review, 2026-09-29.** This follows [decision 0006](decisions/0006-invent-techniques.md), whose direction the user accepted the same day: the system invents techniques, and the first project starts from the mass-mean probe ([seed](../projects/probe-techniques/seed.md)). Nothing here is built. Section 8 lists what needs a yes before the first pilot is planned.

## 1. In one page

- **Inventing techniques is the system's second task** (critiquing arguments was the first). It gets its own versions of the manual's operators, its own readers and its own scoring. The core, the pipeline and the explorer stay shared.
- **The operators are rewritten for technique invention, not reused word for word.**
  - The manual stays the reference: each operator keeps its mechanism.
  - Each task (critiques, techniques, anything later) gets its own wording, examples and output.
  - A test makes sure every manual operator is either rewritten for a task or marked as not applying, with a reason.
- **Scoring:** novelty is never treated as "more is better".
  - The pilot scores every technique under three scoring systems (section 3). It then checks which one agrees with you, separates good from bad, and stays stable.
  - The view you want, techniques that are novel *and* feasible *and* useful, is a figure and a filter, not a single number.
- **Models:** Claude through `claude -p` and your GPT-OSS 20B go behind one interface. Every call is traced the same way, whichever model answered.
- **The interface grows out of the explorer,** starting with a screen where you review and approve each rewritten operator next to the manual's original.

## 2. What the scores mean

Each score answers one question. Examples use techniques that grow out of the mass-mean probe.

| Score | The question | A technique that scores high | One that scores low |
| --- | --- | --- | --- |
| **Soundness** | If built exactly as described, would it do what it claims? Is the maths right, are its assumptions about models plausible, and does it measure the thing it names rather than a confound? | Compares the axis across layers after aligning the layers' bases, and checks the alignment against a random baseline | Claims to find "the model's belief" from a direction that any difference in sentence length would also produce |
| **Feasibility** | Could it be built and run with what we have: an RTX 5070 Ti (16 GB), GPT-OSS 20B or smaller open-weights models, days not months, and no retraining of big models? | Needs forward passes and a few thousand activations | Needs gradients through a 70B model, or labelled data nobody has |
| **Usefulness** | If it works, what can a researcher learn or do that they could not before, and how generally? | Shows whether the model *uses* the axis, not just whether it is readable | Reports the same position the seed already gives, with more steps |
| **Novelty** | Is the idea new, and how far is it from what a model proposes by default? | A technique no model reached without an operator, and that no known method does | Whitening the axis (already known, and the first thing a model suggests) |

Soundness and feasibility are independent:
- A sound technique can be infeasible (it needs retraining a frontier model).
- A feasible one can be unsound (easy to compute, but it measures a confound).

Usefulness is what makes either matter.

**Novelty is measured twice, and never multiplied into fitness:**
- *Measured* against the model's own defaults, by tiers and embedding distance, exactly as in the critique pilot.
- *Judged* against known techniques, by the `precedent` reader: `known`, `variant` or `new`.

A small twist that is new and useful should be able to win. Novelty therefore shapes *selection* (diversity pressure, the brief's Pareto machinery) and the *views* you look at, not the fitness score itself.

## 3. How others score inventions

| Source | What it scores | What we take from it |
| --- | --- | --- |
| **The standard definition of creativity** (Runco and Jaeger, 2012) | An idea is creative when it is both original and effective | The two-part test: new *and* useful, neither alone |
| **Consensual assessment** (Amabile) | Experts rate independently, and their agreement is the measure | Several judges, and agreement as evidence the scale means something |
| **Patent examination** | Novelty (not anticipated), inventive step or non-obviousness (not obvious to a skilled practitioner), utility or industrial application, and enablement (described well enough to build) | "Non-obvious" is not "most novel": a small twist qualifies. Enablement is our `specified` reader |
| **The Heilmeier catechism** (DARPA) | What are you trying to do? How is it done today, and what are its limits? What is new, and why will it work? Who cares? What are the risks, the cost, the time? What are the mid-term and final exams? | A structured case for a technique, and "exams": the cheapest test |
| **TRIZ** (Altshuller) | Ideality: benefits over costs plus harms. Levels of invention, from 1 (routine fix) to 5 (new principle) | Level as a *descriptor*, kept apart from how good the technique is |
| **Technology readiness levels** (NASA) | How close to working: from principle observed, to shown in a lab, to deployed | A plain feasibility scale |
| **Value of information** (decision analysis) | Expected value of running an experiment: the chance it works times what that is worth, plus what is learned if it fails, minus its cost | Suits a lab that *tries* techniques. A cheap, informative test is worth more than an expensive sure thing |
| **ML reviewing** (NeurIPS: quality, clarity, originality, significance), and the large human study of LLM research ideas (Si, Yang and Hashimoto, 2024: novelty, excitement, feasibility, expected effectiveness, overall) | Research ideas and papers | The study found LLM ideas were rated more novel than experts' but slightly less feasible. That is the trade-off to watch |

## 4. Scoring systems to compare

Each system is a rubric the judge fills in, plus a formula for fitness. They are scored separately, never in the same call, so one cannot anchor another.

| | System | Rubric (0 to 1 unless stated) | Fitness | How it treats novelty |
| --- | --- | --- | --- | --- |
| **A** | **Useful and feasible** (the creativity standard) | usefulness, feasibility, soundness, clarity | `usefulness × feasibility`, capped at 0.5 if unsound or under-specified | Not in fitness. Measured and judged separately, and used for selection and views |
| **B** | **Examiner** (patent-style gates) | new (yes/no), non-obvious to a practitioner given the seed (yes/no), useful (0 to 1), enabled: could be built from the description (yes/no) | `useful` if all three gates pass, otherwise half of it | Only "is it new" and "is the twist non-obvious", never "how new" |
| **C** | **Worth trying** (value of information) | chance it works, value if it works, what we learn if it fails, cost to test (hours on the 5070 Ti) | `(p × value + (1 − p) × learning) / cost` | Implicitly, through what we learn. Surprising results are informative |
| D | **Heilmeier case** (a candidate for later) | clear goal, advance over current practice, why it will work, impact, risk, cost, has an exam | the mean of the six, less risk | Only as "advance over current practice" |
| E | **ML reviewer** (a literature reference) | novelty, excitement, feasibility, expected effectiveness, overall | overall | Mixed into overall, so it is useful mainly to compare with published studies |

**For the pilot: A, B and C.** A says what you asked for, B tests the "small non-obvious twist" view, and C suits trying techniques on your GPU. D and E are ready if those three disagree in a way that needs a tie-breaker.

**How to tell which gives insight:**

| Test | What it checks |
| --- | --- |
| Agreement with you | Rank agreement with your blind ratings. The strongest test |
| Discrimination | Does it spread techniques out, or give everything 0.6? |
| Stability | The same technique scored twice by the same judge |
| Judge agreement | Claude against GPT-OSS on the same system |
| Overlap | How much the top 20 under each system differ. If they barely differ, keep the simplest |
| Your quadrant | Does it rank highly the techniques you would pick: novel, feasible and useful? |

## 5. Operators for technique invention

### How a task gets its operators

- **The manual stays the reference.** Its 26 operators go into a registry exactly as written: id, family, name, prompt, when to use, why it works. It is hashed against the PDF.
- **Each task rewrites each operator** in one file, `domains/technique-invention/operators/L1-01.md`.
  - The file header records which manual operator it derives from, the manual's hash, and a status (`draft` or `approved`).
  - The body keeps the manual operator's *mechanism* in the task's own words and examples. It stops there: the output format and the task description are added by the task, once, not repeated in 26 files.
- **Every manual operator is covered.** It is either rewritten, marked `pool` (it acts on the whole population of ideas, not on one idea), or marked `not-applicable` with a reason. A test enforces this.
- **A changed manual flags its variants.** If the manual's hash changes, every variant derived from it drops back to `draft`.

### The 26 operators, and the proposed treatment

| Family | Operator | Technique invention |
| --- | --- | --- |
| Logical | L1-01 Inversion of Core Assumptions | rewrite |
| | L1-02 Minimal Intervention, Maximal Shift | rewrite |
| | L1-03 Discord Injection | rewrite |
| | L1-04 Anti-Pattern Design | rewrite |
| | L1-05 Constraint Liberation | rewrite |
| Structural | L2-01 Latent Role Mutation | rewrite |
| | L2-02 Fractal Expansion | rewrite |
| | L2-03 Recursive Scaffold Echoes | rewrite: where does the seed's structure (contrast, mean, axis) reappear elsewhere? |
| | L2-04 Collapse–Expand Cycling | rewrite |
| Interpretive | L3-01 Frame Collision | rewrite, with frames drawn from measurement disciplines |
| | L3-02 Symbolic Drift Mapping | pool |
| | L3-03 Dual-Axis Reframing | rewrite |
| | L3-04 Mirror Refraction | rewrite: probe the probe |
| Dynamic | L4-01 Temporal Reversal Reasoning | rewrite |
| | L4-02 Metastability Probe | rewrite |
| | L4-03 Gradient Repainting | rewrite |
| | L4-04 Catastrophic Grace | rewrite |
| Contextual | L5-01 Minimal Container Expansion | rewrite |
| | L5-02 Emergent Boundary Crossing | rewrite: across layers, models and modalities |
| Dialectical | L6-01 Discordant Harmonization | rewrite |
| | L6-02 Negative Capability | rewrite |
| | L6-03 Paradox Looping | not applicable, proposed: it acts on a running system's instructions, and a technique has none. Open to your view |
| | L6-04 Archetype Inversion | pool: invert the most common kind of technique in the population |
| Meta | L7-01 Discordant Colony Iteration | core: combines operators, no task wording |
| | L7-02 Operator Chain Governance | core: the scheduler |
| | L7-03 Meta-Reflection | core: analysis of which operators moved the population |

That gives 21 rewrites, 2 pool operators, 3 handled by the core, and 1 proposed as not applicable.

### Draft rewrites, for the tone and level of detail

`{technique}` is the parent: the seed at first, then any evolved technique.

**L1-01 Inversion of Core Assumptions.** The technique below rests on assumptions about how a model represents things. Name one precisely: for example, that the difference between two concepts lies along one direction, or that a class is well summarised by its mean. Assume it is false in a specific, checkable way. What must be true of the model's representations instead? Design a technique that only works, or is only needed, if the inverted assumption holds.

**L1-05 Constraint Liberation.** The technique below works inside constraints: labelled contrast sets, one layer, one token position, a linear readout, one model. Choose one and remove it entirely. What becomes possible? Design the technique that exists only once that constraint is gone. Then remove a second one and see whether the design changes.

**L2-01 Latent Role Mutation.** Each part of the technique below has a job. The contrast sets choose what to compare, the means summarise, the difference defines an axis, and the projection measures a position. Give one part a different job: use the axis as a ruler for something it was not built to measure, or use the positions as a training signal, or make the contrast sets the output rather than the input. Design the technique that results.

**L3-01 Frame Collision.** Describe the technique below as if it were a method in {frame_a}, and again as a method in {frame_b}. Each field has instruments the other lacks. Merge the two methods into one, without deciding which field is right, then translate the merged method back into a technique on a language model's activations. Say what each field contributed.

**L4-04 Catastrophic Grace.** Assume the technique below fails on some inputs: positions that are wrong, unstable across layers, or contradicted by what the model does next. Do not fix the failures. Design a technique that uses them as its signal: where it fails, how often, and what the failing inputs share.

## 6. Architecture

The pieces are those in the design outline ([`design.md`](design.md) sections 3, 6, 7 and 8); this is where technique invention lands in them.

```
operators/cefm.yaml                     the manual's 26 operators, verbatim, hashed
domains/<task>/
  domain.yaml                           essence form, kinds, fields, output format
  readers.yaml                          the lenses
  scoring/<system>.yaml                 rubric, fitness formula, caps (A, B, C, ...)
  operators/<id>.md                     the task's version of each operator
  frames.yaml                           frames for the collision operator
projects/<project>/                     project.yaml, seed or problem, per-project overrides
core/
  models/                               one Backend protocol, two backends
    claude_cli.py                       `claude -p`: isolated (no tools, strict MCP, empty cwd), JSON out, resume for "push for more"
    openai_compat.py                    any OpenAI-compatible server: GPT-OSS 20B via Ollama, LM Studio, llama.cpp or vLLM
  trace.py                              every call recorded the same way: prompt, completion, usage, backend, model, parameters
  prompts.py                            composes system + operator + parent + output format; hashes each part
  registry.py, packs.py, scoring.py     loaded and checked against schemas
explorer/                               unchanged contract; new screens below
```

**What keeps it clean:**
- **One place per concept.** An operator's mechanism is in the registry, its task wording in the variant, the output format in the task, a model's details in its backend, and a score's formula in its scoring file. Nothing is written twice.
- **Tasks are data, not code.** A third task is a new folder. A test fails if the core ever names a task, an axis or an operator.
- **Models are interchangeable.** A role (generator, reader, judge) names a backend and a model in `project.yaml`, so Claude and GPT-OSS can swap in any role.
  - GPT-OSS runs locally for free, so it can be a third generator (does a small local model have different defaults?), a third judge, and, later, the model the invented techniques are *tested on*.
- **Everything is replayable.** Any trace can be re-run on another backend, which is also how the local-model track starts.
- **Tests without model calls.** Recorded traces and a fake backend cover the pipeline. Live calls are opt-in.

## 7. The interface

In order of use:
1. **Operators review.** The manual's operator and the technique version side by side, with the difference highlighted. You mark each one *approved* or leave a comment. This replaces reading 21 files, and the pilot waits on it.
2. **Technique cards** in Explore and the Table:
   - the procedure as numbered steps;
   - what it reveals, and its cheapest test;
   - its scores under each system;
   - a "want to try" mark that fills a queue.
3. **Scoring comparison:** the same techniques ranked under A, B and C side by side, how much they agree with each other and with you, and a novel × useful × feasible 3D view with your quadrant highlighted.
4. **Studio (after the pilot):** set up a run (seed, operators, models per role, budget), launch it, and watch ideas arrive live. The run is a separate process, so the page never blocks.

## 8. The first pilot: what I would want in it

**Questions:**
1. Do the rewritten operators produce techniques outside a model's defaults (tier 3) that are still feasible and useful?
2. Which scoring system (A, B or C) tracks your judgement best, and surfaces the techniques that are novel, feasible and useful?
3. Does a second generation, bred from the best of the first, improve without collapsing into one family?
4. Do the judges mark down unfamiliar techniques relative to you, as the critique pilot suggests?

**Generators:** Claude Sonnet and Opus through `claude -p`, and GPT-OSS 20B locally.

**Arms:**
- **Baseline:** "propose techniques that go beyond this one", pushed until two rounds come back empty. The cap is 12 this time, and recorded; the critique pilot's seeded arms stopped at 4.
- **Plain prompting:** "think of more, genuinely different ones", which is the control.
- **Operators:** 8 rewritten operators, one or two per family, applied to the seed, with 2 repeats per generator.
- **Generation 2:** the best and most diverse of generation 1 (by system A's fitness, with family quotas) get the operators again. This is where "evolution" starts to be tested.

**Evaluation:** the same essences, verified merges, tiers, distances and anchored layout as the critique pilot, plus:
- the six readers;
- scoring under A, B and C by one Claude judge and GPT-OSS (the second Claude judge on a sample);
- you rating a blind sample of about 30 techniques on four questions: useful, feasible, new to you, would you try it.

**Outputs, in the explorer:**
- the 3D map of techniques;
- the novel × useful × feasible view;
- scoring-system agreement;
- operator yield by family;
- generation 2 against generation 1;
- the "want to try" queue.

**Rough size:**
- About 150 generation calls, giving roughly 400–700 techniques.
- Readers and scoring dominate the rest. Reading each technique once, with all six questions in one call, and scoring three systems with one judge plus GPT-OSS comes to about 4–5 thousand calls.
- A few hours with Claude and GPT-OSS running in parallel. The exact plan comes after your yes.

**Order of work:**
1. The registry and task loading, the two backends and tracing.
2. The operators review screen, where you approve the 21 rewrites.
3. The pilot's run scripts.
4. The run itself, in a fresh session.
5. The new screens.

## 9. What I need from you

1. **Scoring:** A, B and C for the pilot? Anything you would add or drop?
2. **Operators:** is the treatment table right, especially marking L6-03 as not applicable and L3-02 and L6-04 as pool operators? And is the tone of the five drafts what you want?
3. **GPT-OSS:** which server runs it (Ollama, LM Studio, llama.cpp or vLLM), and at what address? The backend only needs the OpenAI-compatible URL and model name.
4. **Core code:** `CLAUDE.md` holds feature code until design v1.0. I propose settling design sections 6 to 8 (packs, the model layer, traces) as v1.0 slices now, so the registry, backends and tracing are built as core, properly, and not as pilot code to be thrown away. That needs a decision record, 0007, if you agree.
