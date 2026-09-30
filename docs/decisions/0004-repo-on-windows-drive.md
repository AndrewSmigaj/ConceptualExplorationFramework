# 0004: The repo lives on the Windows drive

- **Status:** Accepted
- **Date:** 2026-09-19
- **Supersedes:** [0002](0002-repo-location-and-line-endings.md), on location only. Its line-ending rules still stand.

## Context

[0002](0002-repo-location-and-line-endings.md) put the repo on the WSL filesystem for speed. In practice it wasn't reachable from the editor the user actually works in. VS Code blocks `\\wsl$\…` paths unless `security.allowedUNCHosts` lists them, and applying that setting needs a reload or restart. The user has several VS Code windows open and can't restart, and the WSL folder stayed invisible in the window they work in.

A repo you can't open is worse than a repo with slower file I/O.

## Decision

The repo lives at `C:\Users\<you>\ConceptualExplorationOperators`, which is `/mnt/c/Users/<you>/ConceptualExplorationOperators` from WSL. It is the folder the user already has open.

- It was copied there with its full git history. The source-text hashes were verified byte-for-byte afterwards.
- `core.fileMode` is `false` in this repo, because the Windows drive reports every file as mode 0755 and git would otherwise show every file as modified.
- The WSL copy at `~/ConceptualExplorationOperators` is kept for now as a backup, and removed once the user confirms this one works. **Only one copy may be worked in.** This one is it.

## Consequences

- **The line-ending rules from 0002 still hold**, and matter more now. `.gitattributes` keeps LF for text and leaves `projects/*/sources/**` and `inputs/**` untouched. Windows editors can write CRLF, so the quote-normalization question ([OI-07](../open-issues.md)) stays open and gets tested on this drive.
- **File I/O is slower** across the Windows boundary. It shows up when runs write thousands of small files into `traces/`, `inbox/` and `dispatch/`. Revisit if a cycle turns out to be I/O-bound: either batch the writes, or keep only the hot directories on the Linux side.
- **The original input files stay in this folder**, untracked and git-ignored. The tracked byte-exact copies are in `inputs/` and `projects/*/sources/`.
- `.venv` was rebuilt here. It is git-ignored.
