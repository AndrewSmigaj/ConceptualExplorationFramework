# 0007: One public repository, on WSL's own disk

- **Status:** Accepted
- **Date:** 2026-10-01
- **Supersedes:** [0004](0004-repo-on-windows-drive.md) (the repo on the Windows drive), and the earlier arrangement in which a private working repository was filtered into this public one.

## Context

Until now there were two repositories:
- **a private working folder** on the Windows drive, which held everything, including an earlier critique pilot and its two example problems, which may not be published;
- **this public repository**, a filtered copy built from that folder by a script that removed the withheld material and scanned the result.

The withheld material is in every commit of the working folder's history, so that folder could never be pushed, and nothing backed it up.

Two things changed:
- **The work no longer needs the withheld material.** The system's main task is now inventing techniques ([0006](0006-invent-techniques.md)), with a public seed. The critique pilot is finished, and was only ever for the assignment it was written for.
- **The Windows drive is slow for this work.** Measured from WSL on 2026-10-01:

  | Operation | Windows drive (`/mnt/c`) | WSL's own disk |
  | --- | --- | --- |
  | Importing `torch` and `sentence-transformers` | 12 s and 81 s | 9.6 s together (3.2 s warm) |
  | Reading model weights | 129 MB/s | typically 1–1.5 GB/s |

  The local model server, with a GPU build of PyTorch several GB in size, would be slower still.

[0004](0004-repo-on-windows-drive.md) moved the repo to the Windows drive only because VS Code blocked `\\wsl$\…` paths. Opening the folder with `code` from a WSL terminal avoids that: it opens a window connected to WSL through VS Code's WSL extension, and no UNC paths or restarts are involved.

## Options

1. Keep both repositories, move the private one to WSL, and back it up to a private GitHub repository.
2. **Work directly in this public repository, and move the private material into its own archive.**

## Decision

**Option 2.**
- **Where it lives:** this repository is where the work happens, at `~/ConceptualExplorationFramework` on WSL's disk, pushed to `github.com/AndrewSmigaj/ConceptualExplorationFramework`.
- **The archive:** the old working folder, with its full history, the pilot, the example problems and the blind-rating sessions, becomes `~/critique-pilot-archive`. It is backed up to a private GitHub repository and is never copied into this one.
- **The check before every commit:** `tools/check_withheld.py` runs as a pre-commit hook. It reads its patterns and the withheld texts from the archive, and stops any commit that contains a withheld pattern or shares eight consecutive words with withheld text. The patterns live in the archive, because the words themselves would reveal what is withheld.
- **The old filtering script retires** with the old working folder.
- **Model weights move to WSL's disk too,** at `~/models/`. One shared copy is read by every project that loads them.

## Consequences

- **The hook is enabled per clone** (`git config core.hooksPath tools/hooks`). A fresh clone on another machine has no archive and no hook, which is fine: only this machine holds withheld material.
- **The explorer can still serve the pilot's dataset**, including the blind-rating sessions, from the archive's folder. The dataset never enters this repository.
- **Passages of the design that used the withheld examples stay marked as withheld.** New examples come from the technique-invention task.
- **The line-ending rules of [0002](0002-repo-location-and-line-endings.md) still hold.** `core.fileMode` can be `true` again on WSL's disk.
- **The old Windows-drive copies are kept until the user has checked the new setup,** then deleted with their agreement.
