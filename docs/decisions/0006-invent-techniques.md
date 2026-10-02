# 0006: The system invents techniques, starting with probing

- **Status:** Accepted in direction, 2026-09-29. The details (operators, readers, scoring systems, the pilot) are worked out in [`technique-invention.md`](../technique-invention.md), which is under review.
- **Date:** 2026-09-29

## Context

The system was designed around one kind of idea, critiques of a written argument (brief Appendix A), and the pilot tested it on two arguments. Those arguments cannot be published (see the README of the public copy), so the public repository needs a different example.

The user wants more than a new example. They want the system to invent rather than critique: to propose and try new techniques. The first domain is mechanistic interpretability, starting from linear probing. The user's own paper uses a mass-mean probe to find two internal representations and place a token along the axis between them, so that is the seed.

## Options

1. **Keep critique as the main task**, with a new public argument to critique.
2. **Make technique invention the main task.** Keep the critique pilot as finished, private evidence.
3. **Run both as equal tasks.**

## Decision (proposed)

**Option 2.** The system's main task becomes inventing techniques, and its first project is `projects/probe-techniques/`, seeded with the mass-mean probe ([`seed.md`](../../projects/probe-techniques/seed.md)).

What carries over unchanged:
- **The paradigm.** A model's default output is measured by exhausting it, operators push past it, and tiers and distance say how far each idea is from the default. Judges and a blind human rater score familiar and unfamiliar ideas alike.
- **The pipeline:** essences, verified merges, tiers and anchored layouts.
- **The explorer,** which is domain-neutral.

What changes is the domain pack, sketched below from the brief's Appendix B.2 (`problem-solving`).

### Sketch: the `technique-invention` pack

**Essence form:** "Compute X from a model's activations in order to learn Y." Two ideas with the same procedure and the same purpose produce near-identical essences.

**Kinds:**
- `technique`: a new way to learn something.
- `variant`: a small change to a known technique.
- `observation`: something about the problem that is not itself a technique.

Only techniques and variants are exported, and all kinds stay available as parents.

**Fields each idea carries:**
- `procedure`: numbered steps, concrete enough to implement.
- `reveals`: what it would tell a researcher that the seed cannot.
- `cheapest_test`: the smallest experiment that could show it fails.

**Readers (lenses):**

| Lens | Question | Output |
| --- | --- | --- |
| `precedent` | What is the closest known technique, including the seed, and exactly how does this differ? | Text, plus a verdict: `known`, `variant` or `new` |
| `specified` | Could a researcher implement it from the procedure alone? Name any step that is missing. | Bool plus the missing steps |
| `reveals` | What would it show that the mass-mean probe cannot? If nothing, say so. | Text. If nothing, `kind: variant` |
| `assumptions` | What must be true about the model's representations for it to work? | Text |
| `cheapest_test` | The smallest experiment, on an open-weights model with one GPU, that would show it fails. | Text |
| `adversary` | Its most likely failure (a confound, a degenerate case, no gain over the seed), then what survives. | Text |

**Scores (0 to 1):**

| Score | Meaning |
| --- | --- |
| `novelty` | New to the literature, not just to the model |
| `soundness` | Its maths and its assumptions about models hold |
| `insight` | How much a researcher would learn if it works |
| `feasibility` | Doable on an open-weights model with one GPU |
| `clarity` | Unambiguous about what to compute |

**task_fitness** = `soundness × insight`:
- capped at 0.5 when `specified` is false;
- capped at 0.5 when `precedent` says `known`;
- zero only when `soundness < 0.5`, meaning it asserts something false.

The caps multiply, as in Appendix A.

## Consequences

- **The brief gains an appendix for this pack** once this record is accepted, and the public copy's withheld sections point to it. The brief's statement of intent (critiques of arguments) is amended at the same time, recorded here.
- **New worked examples** of the cap arithmetic are written for this pack. The old ones used the withheld problems.
- **The design outline's configuration and evaluation sections** gain this pack as their second worked case, which is also the brief's leak test.
- **A pilot for this task follows the critique pilot's shape.**
  - Exhaust the seed's default improvements with both models, then push past them with the operators.
  - Tier and place every technique.
  - Have both models score them, and the user rate a blind sample.
  - Generation makes model calls, so it runs in a fresh session.
- **Nothing is built until the user has reviewed** the seed and this pack sketch.

## Answers so far (2026-09-29)

- **Inventing, not critiquing,** is the direction. Technique invention gets its own versions of the manual's operators, not the same wording.
- **Scoring:** the task gets its own scoring. Feasible and useful are required. Novelty must not count as "more is better", since a small twist can be what makes the difference. Several scoring systems are to be tried to see which gives insight. The user wants to see techniques that are novel and also feasible and useful.
- **Hardware:** an RTX 5070 Ti, running GPT-OSS 20B locally.
- **Software:** it should be well designed, maintainable and extensible, with a good interface and both `claude -p` and the local model.

The pack sketched above is superseded by the design pass, which replaces the single score with three scoring systems to compare.

## Open questions for the user (first round)

1. **The scores.** Are novelty, soundness, insight, feasibility and clarity the right five, and is `soundness × insight` the right measure of fitness?
2. **"One GPU".** The roadmap assumes an RTX 5070 Ti (16 GB). Should techniques be limited to what that runs, and on which open-weights models?
3. **Testing.** Should the system eventually run a technique's cheapest test itself, on the local-model track, or does a human decide which ones to try?
