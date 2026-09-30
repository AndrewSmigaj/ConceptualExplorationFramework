# 0001: Decision records and document roles

- **Status:** Accepted
- **Date:** 2026-09-18

## Context

The brief says what the system is for, but it leaves many engineering choices open or contradictory ([open-issues.md](../open-issues.md)). The project is also a measurement. Whether an operator helped depends on exactly which prompt, threshold and rule was in force when it ran. Six months from now, we need to know why each choice was made and when it changed.

## Options

1. Edit the brief in place as decisions get made.
2. Keep a separate engineering design document, plus one short record per decision.

## Decision

Option 2.

- **`brief.md`** is the research spec: what and why. It is amended only when the research intent changes, and each amendment has a decision record.
- **`design.md`** is the engineering design: how. Each resolution in it is marked **Proposed** or **Decided** and links to its open-issue id.
- **`decisions/NNNN-slug.md`** holds one record per decision: status, date, context, options, decision, consequences.
  - Numbers are never reused.
  - A superseded record stays in place, marked Superseded, and names the record that replaced it.
- **`open-issues.md`** closes a row only by linking its decision record and design section.

## Consequences

- Every change to the design is a reviewable git diff with its reasons attached.
- Records are short, one page at most. A decision that needs more space belongs in `design.md`, and its record links there.
- The brief stays readable as the statement of intent, rather than piling up engineering detail.
