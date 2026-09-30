# 0005: The explorer app is built now, as its own component

- **Status:** Accepted
- **Date:** 2026-09-26

## Context

The pilot has produced 1,104 critiques, with essences, features, tiers, distances and scores from two judges. The user wants a proper web app, not a throwaway page, to do four things:
- explore the ideas;
- see the whole cloud and its clusters;
- colour and size points by any value;
- produce the proposal's figures from the same data.

It will also be the project's viewer (brief §13, roadmap M13).

Two existing rules stood in the way:
- `CLAUDE.md` allows no feature code until design v1.0 is approved.
- Pilot code in `experiments/` is throwaway by definition.

The pilot's first page was a card list rendered from inside a Python string. It already showed how quickly such a page goes stale.

## Options

1. Build it properly inside the pilot's folder. This is quick, but it ties the app to one experiment and contradicts `experiments/` being throwaway.
2. Start core milestone M13 now. That means feature code before design v1.0.
3. Make a separate top-level component, `explorer/`, that reads a documented data contract. The pilot writes that contract through an adapter, and the core system writes it later.

On runtime, the choice was between static files opened from `file://`, which is what brief §13 says, and a small local server.

On the frontend, the choices were plain JS modules, Vite with TypeScript, or Vite with TypeScript and Svelte.

## Decision

- **Option 3.**
- **`explorer/` is exempt** from the design-phase rule, in the same way `experiments/` is.
- **It stays domain-neutral** under the same rule as core (brief §2):
  - It never names a domain's axes, arms, judges or tiers.
  - It renders whatever fields the dataset declares.
- **Import boundaries:**
  - It never imports from `experiments/` or `core/`.
  - Adapters live with the data they convert.
- **Runtime:** a local Python server (FastAPI) serves the built frontend and a small API, opened at localhost from the Windows browser. There are no network dependencies, and Plotly is bundled rather than loaded from a CDN.
- **Frontend:** Vite + TypeScript + Svelte, in `explorer/web/`.
- **The data contract** is `explorer/schema/dataset.schema.json`, versioned.
  - A dataset is a directory: a read-only `dataset.json`, plus `annotations/` that only the server writes (ratings, notes).
- **Projections and clusters** are computed once in Python with fixed seeds, never in the browser.

## Consequences

- **Brief §13 and roadmap M13 said "no server, data inlined as JS"** to get around a `file://` page being unable to fetch JSON ([OI-53](../open-issues.md)). A server removes that problem. It also lets the app write ratings and notes directly to disk, which the blind-rating screen needs. [`design.md`](../design.md) §22 records the change as **Proposed**. OI-53 stays Open until §22 is Decided.
- **Blind rating is enforced by the server.** The rating endpoint returns only the argument, the rubric and the texts. The key is served only after the session is complete. This is tested.
- **The repo gains a Node toolchain.** `node_modules/` and `explorer/web/dist/` are git-ignored, and building the frontend is one documented command.
- **Python dependencies** for the app sit in their own uv dependency group, `explorer`, so core stays unaffected.
- **The explorer is built in milestones E0–E5**, one branch each, and the user reviews each exit.
- **When core reaches M13**, it writes the same contract rather than building a second viewer. Contract changes bump `schema_version`.
