# 0002: Repo location and line endings

- **Status:** Superseded on location by [0004](0004-repo-on-windows-drive.md). The line-ending rules below still stand.
- **Date:** 2026-09-18

## Context

- **Where the project started.** It began in `/mnt/c/Users/<you>/ConceptualExplorationOperators`, the Windows drive as seen from WSL2.
- **I/O speed.** File I/O across that boundary is several times slower than on the Linux filesystem. This system writes thousands of small files: traces, inbox entries, dispatch lists.
- **Line endings.** The brief arrived with CRLF line endings.
- **Byte-exact matching.** Mechanical quote verification (brief §7.2) matches exact bytes against the source texts, and prompt hashes (§12) are byte-sensitive. A tool silently converting line endings would break both, and nothing would say so.

## Options

1. Stay on `/mnt/c` and add `.gitattributes`.
2. Move to the WSL filesystem and add `.gitattributes`.

## Decision

Option 2.

- **Location.** The repo lives at `~/ConceptualExplorationOperators`. From Windows it is reachable at `\\wsl$\Ubuntu-22.04\home\<you>\ConceptualExplorationOperators`.
- **The original folder.** The copy on `/mnt/c` is left untouched.
- **`.gitattributes`:**
  - forces LF for text files;
  - marks `projects/*/sources/**` and `inputs/**` as `-text`, so git never converts their bytes.
- **The brief.** `docs/brief.md` is the brief with CRLF converted to LF and nothing else changed. It is not a quote source, so the conversion is safe.
- **Inputs.** Source texts and the CEFM manual are copied byte-exact, and their SHA-256 hashes are recorded in `inputs/MANIFEST.md`.

## Consequences

- **Windows editors open the repo through its `\\wsl$` path.** The steps for adding it to an existing VS Code window are in the [README](../../README.md#where-this-repo-lives).
- **The original `/mnt/c` folder is a separate copy of the inputs, not the repo.** Edits made there do not reach the repo, so editing there would fork the work.
- This decision does **not** settle quote normalization: whether quote characters, whitespace and line endings are normalized before matching. That is [OI-07](../open-issues.md). This decision only guarantees that the stored bytes are the bytes provided.
