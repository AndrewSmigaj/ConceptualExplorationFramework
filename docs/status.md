# Status

Read this first when starting or resuming a session.

The repo is at `C:\Users\<you>\ConceptualExplorationOperators`, which WSL sees as `/mnt/c/Users/<you>/ConceptualExplorationOperators`. It moved here from WSL on 2026-09-19 so it opens in the user's existing VS Code window ([decision 0004](decisions/0004-repo-on-windows-drive.md)).

## Where things stand (2026-09-19)

- **Stage A (organize the repo) is done.**
  - The brief, decision records 0001–0003, the open-issues register (OI-01 to OI-63), a provisional roadmap, human tasks, and the prompt changelog are all in `docs/`.
  - The CEFM manual and both source texts are in the repo, byte-exact. Their hashes are in `inputs/MANIFEST.md`.
- No feature code exists. None gets written until the user approves design v1.0.

## The running experiment

A pilot is under way in `the pilot's `, testing whether reframing an argument through another field finds critiques the model cannot reach directly. Its state of play is [`the pilot's STATUS.md`](../the pilot's STATUS.md); it is paused pending a judge audit.

## The explorer app

`explorer/` is the web app for exploring ideas: the cloud, clusters, figures and blind rating. It was started early under [decision 0005](decisions/0005-explorer-app.md) and is built in milestones E0–E5, one branch each. Its milestone table and run commands are in [`explorer/README.md`](../explorer/README.md). A private pilot is its first data source.

## Next step

**Stage B, step 1 is done: the outline of [`design.md`](design.md) is written and awaiting the user's review.** It has 26 sections plus a glossary, and every issue from OI-01 to OI-63 is owned by exactly one of them, verified mechanically.

Once the user accepts the structure, step 2 is the first draft: fill each section, marking every resolution **Proposed**.

**The sections, as outlined:**
1. Scope, the three purposes, and the acceptance test.
2. Invariants.
3. Architecture, the call path, and the subagent definitions.
4. Isolation and contamination.
5. Data model, state and layout.
6. Configuration: packs, strategies, frames, operators.
7. The model-call layer.
8. Traces, replay and the local-model track.
9. The run manifest.
10. The cycle pipeline (round 1; failure, resume and idempotency).
11. Evaluation: tiers 0 to 2.
12. The reader panel and the judge.
13. Calibration and drift.
14. The tournament.
15. Fitness, retention and families.
16. Selection and the scheduler.
17. Operator and strategy statistics.
18. Arms, baseline and collisions.
19. Metrics and diagnostics.
20. Budget, saturation and stopping.
21. End-of-run analysis.
22. Viewer and export.
23. Testing strategy.
24. Human-in-the-loop work.
25. Risks.
26. What gates what.
Appendix A. Glossary.

## Resuming the conversation that set this up

In a WSL terminal:

```
cd /mnt/c/Users/<you>/ConceptualExplorationOperators && claude --continue
```

That continues the most recent session started in this folder. To pick a specific one, use `claude --resume 2f7a4670-1364-4f42-b189-fa7330eb33b8`.

## Starting fresh instead

Open a session in this repo and read these, in order:
1. `CLAUDE.md`
2. this file
3. `docs/roadmap.md`
4. `docs/open-issues.md`
5. `docs/brief.md`, as needed
