# Prompt changelog

Prompts are experimental apparatus. Rewording one changes the experiment. Every change to a prompt file gets an entry here, newest first.

Before this log's first entry, the prompts in the brief's Appendix A are the baseline. They are extracted verbatim to files when they first come into use. The extraction gets an entry of its own.

**Each entry records:**
- the date and the prompt file;
- the old and new hashes;
- the reason, with a link to its open issue or decision record;
- which runs used the old version.

## Entries

### 2026-09-27 — seeded collision prompt added

`the pilot's prompts/stage-b-collision-seeded.md`, new, hash `1a5dd01b9bd355e5`.

- **What:** the impersonal collision prompt (`stage-b-collision.md`, `59ef3c2719c0fada`), with the seed's problem added under each scenario. The hybrid must contain both known problems, and the reader starts from them. Every other line is unchanged, so the seed is the only difference from the tested prompt.
- **Why:** the seeded design needs a collision arm that starts where the reframes start. The plan is in `the pilot's COLLISION-PLAN.md`, and the user approved it on 2026-09-27.
- **Old version:** none. `stage-b-collision.md` stays as it was.
- **Also recorded:** the manifest now hashes the ten prompts added after the 2026-09-19 freeze. The nine frozen prompts were re-checked and are unchanged.

### 2026-09-19 — pilot prompts frozen

`the pilot's prompts/*.md`, hashes in that experiment's `manifest.md`.

These are pilot prompts, not the system's. They come from the six-condition reframe protocol, with four deviations, all recorded in the experiment's README:

- The cap of ten ideas in condition 1 and Stage B is replaced by the exhaust rule, so counts are comparable across conditions.
- Stage C no longer sees the known critiques and no longer self-reports novelty; both move to blind passes.
- A machine-readable output format was appended to each prompt (marker lines such as `CRITIQUE:`), because `--json-schema` turned out to be a tool call and tool output would not replay on a local model.
- The generators are not shown the H1–H4 step labels, so the task stays the task as posed. The extractor assigns steps afterwards.
