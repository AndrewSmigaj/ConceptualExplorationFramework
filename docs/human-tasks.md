# Human tasks

This is the work only a person can do, and what each piece gates. Hand labelling and rating are part of the experiment's measurement, so none of them can be skipped or delegated to a model.

| Task | Gates | Status | Notes |
| --- | --- | --- | --- |
| Provide the CEFM manual and both source texts | Stage A | Done | Copied byte-exact; hashes go in `inputs/MANIFEST.md` |
| Review the design outline | Stage B, step 1 | — | Structure is settled before any prose is written |
| Review design rounds and approve v1.0 | Stage C | — | Includes accepting each Proposed resolution |
| Approve the call-path decision | M0 exit | — | From the spike results |
| Review the CEFM transcription | M2 exit | — | Claude drafts it; a script diffs it against the manual |
| Label 50 dedup pairs as same or different | M4 exit; any large run | — | Brief §6.4. Done in a CLI labelling tool |
| Write human seeds | M5 onwards | — | Any time after M5. Text, pictures, analogies, half-formed objections |
| Rate 12 calibration anchors, blind | M6 exit | — | Metadata stripped and order shuffled. Exclude your own seeds (brief §4.1) |
| Rate 12 held-out drift anchors, blind | M6 exit | — | Never enter the pool (brief §7.8) |
| Write synthetic anchors for any missing A.7 category | M6 exit | — | Only if round 1 produces none in that category. Kept out of the pool |
| Review the hypothesis translations of "When to Use" | M10 | — | Recorded, never enforced (brief §8.4) |
| Review the export and rewrite the picks | M14 | — | The system produces candidates, never submissions |
| Milestone exit reviews | Every milestone | — | Before the next branch starts |
