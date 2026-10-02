# Idea evolver

The name is a placeholder.

A system for evolving ideas with Claude. It generates ideas and perturbs them with Conceptual Exploration Operators. It judges them through fixed lenses, merges duplicates, and culls with diversity pressure. It then clusters the survivors into families and lets a person browse everything. It also measures whether the operators move a model past its default output.

**Status: design phase.** There is no feature code yet.

## This repository

This is the project's working repository, and it is public. An earlier pilot, which critiqued two example arguments, is kept privately and is not part of it; passages of the design that used those examples are marked as withheld. The Conceptual Exploration Field Manual is in `inputs/cefm/`.

It lives on WSL's own disk (`~/ConceptualExplorationFramework`) because file access there is many times faster than on the Windows drive ([decision 0007](docs/decisions/0007-one-public-repo-on-wsl.md)). Open it in VS Code from a WSL terminal with `code ~/ConceptualExplorationFramework`.

## Documents

| Document | Role |
| --- | --- |
| [`docs/status.md`](docs/status.md) | Where things stand, the next step, and how to resume. **Read first** |
| [`docs/brief.md`](docs/brief.md) | Research spec: what the system is for and why |
| [`docs/design.md`](docs/design.md) | Engineering design: how. Currently an outline awaiting review |
| [`docs/open-issues.md`](docs/open-issues.md) | Gaps and contradictions in the brief that the design must resolve |
| [`docs/decisions/`](docs/decisions/) | One record per decision |
| [`docs/roadmap.md`](docs/roadmap.md) | Milestones. Provisional until design v1.0 |
| [`docs/human-tasks.md`](docs/human-tasks.md) | Labelling, rating, transcription and reviews, and what each one gates |
| [`docs/prompt-changelog.md`](docs/prompt-changelog.md) | Every change to an experimental prompt, with the reason |

## Development

The project uses uv and Python 3.12.

- `uv run pytest` runs the deterministic suite.
- Tests marked `live` make real model calls. They run only with `uv run pytest -m live`.
