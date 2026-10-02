# Status

Read this first when starting or resuming a session.

The repository is `~/ConceptualExplorationFramework` on WSL's own disk, pushed publicly to GitHub ([decision 0007](decisions/0007-one-public-repo-on-wsl.md)). Open it in VS Code from a WSL terminal with `code ~/ConceptualExplorationFramework`. An earlier critique pilot is archived privately at `~/critique-pilot-archive` and never enters this repository; a pre-commit check enforces that.

## Where things stand (2026-10-01)

- **The main task is now inventing techniques** in mechanistic interpretability, seeded with the mass-mean probe ([decision 0006](decisions/0006-invent-techniques.md), [design pass 1](technique-invention.md), [seed card](../projects/probe-techniques/seed.md)).
- **The critique pilot is finished and archived.** Its findings shaped the design; its data stays private.
- **The explorer web app** (milestones E0–E5) is built: the idea cloud, clusters, figures, tables and blind rating.
- **The core foundations are planned** (plan iteration 3.1, approved 2026-10-01). It covers:
  - the model layer (`claude -p` and local PyTorch models);
  - call records;
  - the operator registry and task folders (technique invention and critique);
  - four researched scoring systems, plus pairwise judging with local decision models;
  - prior-art search across several sources;
  - surprise measures, and snapshots of internal states;
  - an approvals page in the web app.

  The plan is at `~/.claude/plans/assess-where-we-were-mutable-seahorse.md` on this machine, and becomes the design documents in step D1.
- No core feature code exists yet. It is written only after design v1.0 is agreed.

## Next steps, in order

1. **Step W, finishing the move:**
   - push the private archive to a private GitHub repository, once the user has created it;
   - copy the model weights to `~/models/`;
   - the user checks the new setup, then the old Windows-drive copies are deleted.
2. **Evidence spikes,** in `experiments/`:
   - **E1:** GPT-OSS on the GPU: load time, Harmony rendering, speed, hooks, memory.
   - **E2:** isolating `claude -p` calls (five calls, with the user's go-ahead).
   - **E3:** positive controls for the surprise measures.
3. **Design documents:**
   - **D0:** the design-review page, built the way the user's other project builds its design-document page.
   - **D1:** `requirements.md`, the `design/` files and decision records 0008–0012, iterated with the user until nothing is left to fix (design v1.0).
4. **Building the foundations,** steps S1–S6, then the technique-invention pilot.

## Waiting on the user

- Choosing two more local mixture-of-experts models and two JEV-style decision models.
- A free Semantic Scholar API key, for the prior-art search.
- Creating an empty private GitHub repository for the pilot archive.

## Starting fresh

Open a session in this repository and read, in order:
1. `CLAUDE.md`
2. this file
3. the plan named above
4. `docs/roadmap.md` and `docs/open-issues.md`
5. `docs/brief.md`, as needed
