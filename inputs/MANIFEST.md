# Inputs manifest

These are external inputs, copied byte-exact. Never edit, reformat or re-save them. See `docs/decisions/0002-repo-location-and-line-endings.md`.

To verify: run `sha256sum <path>` and compare the result with the table.

| Path | SHA-256 | Bytes | Line endings | Provided from | Date |
| --- | --- | --- | --- | --- | --- |
| `inputs/cefm/ConceptualExplorationFieldManual.pdf` | `815cca51484bef58509bbf71040f8fb7c2cbed132496a8ae1adab55d09b474ab` | 446363 | n/a (PDF) | `ConceptualExplorationFieldManual.pdf` in the original project folder; byte-identical to the copy in Downloads (file dated 2026-03-15) | 2026-09-18 |

## Notes

- **Which CEFM version.** An older manual, `Conceptual Exploration Field Manual (CEFM v1.pdf` (dated 2025-10-21, SHA-256 `13aa88bb…afeba`), is also in Downloads. It is not used. The user said either version is acceptable, and this one is the newer.
- **Source texts.** The example problems' source texts are not published (see the README).
- **File names.** Source files are renamed to the paths given in brief Appendix A.6. Only the name changes; the content is byte-exact.
