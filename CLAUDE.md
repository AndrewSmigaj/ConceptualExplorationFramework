# CLAUDE.md

Rules for Claude Code sessions in this repo.

**This file never contains idea content.** That means no critiques, seeds, anchors, frames, and nothing from `pool/`, `inbox/` or the source texts. Anything written here can reach model calls and bias them (brief §3.1).

## Current phase

Design. `docs/design.md` is being written and revised with the user. Write no feature code until the user approves design v1.0.

**`experiments/` is exempt.** Pilot code there is throwaway and exists to produce evidence for the design, not to become the core. It never imports from `core/`, and `core/` never imports from it.

**`explorer/` is exempt too** ([decision 0005](docs/decisions/0005-explorer-app.md)). It is the web app for exploring ideas, and it is not throwaway.
- It follows the domain-neutrality rule below, and renders only what the dataset declares.
- It never imports from `experiments/` or `core/`. Data reaches it only through `explorer/schema/dataset.schema.json`.
- It is built in milestones E0–E5, one branch each.

Read `docs/status.md` first: it gives where things stand and the next step.

## Documents

- `docs/brief.md`: the research spec (what and why). Amend it only when the research intent changes, and record a decision when you do.
- `docs/design.md`: the engineering design (how). Each resolution is marked **Proposed** or **Decided** and links to its open-issue id.
- `docs/open-issues.md`: the register of gaps in the brief. Close a row only by linking its decision record and design section.
- `docs/decisions/NNNN-slug.md`: context, options, decision, consequences.
  - Numbers are never reused.
  - A superseded record stays in place and names what replaced it.
- `docs/prompt-changelog.md`: every change to a prompt file, with the reason. Prompts are experimental apparatus; never paraphrase or tidy one.
- `docs/roadmap.md` and `docs/human-tasks.md`: milestones, and the human work that gates them.

## Rules

- **Isolating runs.** A session that dispatches model calls for a run must not read the contents of any of these:
  - `projects/*/pool/`
  - `inbox/`
  - `traces/`
  - `seeds/`
  - `anchors/`
  - `export/`

  It handles paths and counts only. Do debugging on run output in a separate session.
- **Delegation messages.** Never compose idea content in one. Copy dispatch entries verbatim.
- **Source files.** Files in `projects/*/sources/` and `inputs/` are byte-exact. Never edit, reformat or re-save them. Their SHA-256 hashes are in `inputs/MANIFEST.md`.
- **Domain neutrality.** Core code never names a domain's axes, lenses, kinds or arms, and never assumes how many there are (brief §2).
- **Line endings.** Use LF only (`.gitattributes`). Do not let tools write CRLF.
- **Publishing.** This repo is private and is never pushed to GitHub. The public copy is built by `tools/publish.py` into `../ConceptualExplorationFramework` and pushed from there.
  - `tools/publish.py` withholds the pilot and its example problems.
  - It refuses to publish if any withheld text or marker remains.
  - Its redactions must match exactly, or the build stops.
- **Milestones.** One branch per milestone. The user reviews each milestone's exit before the next one starts.

## Tooling

- uv and Python 3.12.
- `uv run pytest` runs the suite, excluding `live` tests. Run `uv run pytest -m live` only when the user asks.
- `uv run ruff check` for linting.
