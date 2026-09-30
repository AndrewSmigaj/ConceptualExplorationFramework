# 0003: Model calls run on a Claude subscription

- **Status:** Accepted
- **Date:** 2026-09-18

## Context

Every model call in the system has to be paid for somehow. The two routes are a Claude subscription used through Claude Code, or an API key with Console billing. Choosing one fixes which call paths and features are available.

## Decision

All model calls run through Claude Code on the user's subscription login, either as subagents or as `claude -p`. There is no API key.

## Consequences

- **No `--bare` mode.** It requires an API key. `claude -p` therefore loads user-level context by default, so isolating each call has to be done another way ([OI-02](../open-issues.md)).
- **No Batches API discount, and no direct control of sampling parameters.** Temperature can't be set or recorded ([OI-11](../open-issues.md)).
- **Throughput is bounded by plan rate limits.** Budgets are planned in tokens and wall-clock hours, not dollars. The `total_cost_usd` in `claude -p` output is a client-side estimate only ([OI-54](../open-issues.md)).
- **Token accounting.** It comes from `claude -p` JSON usage or from subagent transcripts, whichever call path M0 selects ([OI-01](../open-issues.md)).
- **Revisiting.** If a later phase needs exact sampling control or batch pricing, supersede this record. Don't work around it.
