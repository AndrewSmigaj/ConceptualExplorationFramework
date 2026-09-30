"""Command line: `uv run python -m explorer <command>`.

  validate  check a dataset directory against the contract
  enrich    add projections and clusterings; new ideas are placed into the saved layout
  serve     run the local server: the app, the API, and blind rating
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from explorer.contract import ContractError, load_dataset

SHOW_PROBLEMS = 20


def report(err: ContractError) -> None:
    """Print the first problems and a count, not thousands of lines."""
    for p in err.problems[:SHOW_PROBLEMS]:
        print(p, file=sys.stderr)
    if len(err.problems) > SHOW_PROBLEMS:
        print(f"... and {len(err.problems) - SHOW_PROBLEMS} more", file=sys.stderr)


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        data = load_dataset(args.dataset)
    except ContractError as err:
        report(err)
        print(f"INVALID: {len(err.problems)} problem(s) in {args.dataset}", file=sys.stderr)
        return 1
    print(f"valid: {len(data['ideas'])} ideas, {len(data['fields'])} fields, "
          f"{len(data['scorers'])} scorers")
    return 0


def cmd_enrich(args: argparse.Namespace) -> int:
    from explorer.enrich import enrich

    try:
        data, status = enrich(args.dataset, refit=args.refit)
    except ContractError as err:
        report(err)
        return 1
    print(f"layout: {status}")
    for pid, proj in data["projections"].items():
        extra = f", explained variance {proj['explained_variance']}" \
            if "explained_variance" in proj else ""
        print(f"projection {pid}: {len(proj['coords'])} points{extra}")
    for cid, cl in data["clusterings"].items():
        noise = sum(1 for k in cl["assignments"].values() if k == -1)
        sizes = [c["size"] for c in cl["clusters"]]
        print(f"clustering {cid}: {len(sizes)} clusters, sizes {sizes}, {noise} unclustered")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from explorer.contract import load_dataset
    from explorer.server import WEB_DIST, create_app

    try:
        data = load_dataset(args.dataset)
    except ContractError as err:
        report(err)
        return 1
    if not (WEB_DIST / "index.html").exists():
        print("note: the frontend is not built; only /api is served. Build it with:\n"
              "  cd explorer/web && npm run build", file=sys.stderr)
    print(f"{data['meta']['title']}: {len(data['ideas'])} ideas")
    print(f"open http://localhost:{args.port}")
    uvicorn.run(create_app(args.dataset), host=args.host, port=args.port, log_level="warning")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="explorer")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="check a dataset directory against the contract")
    p.add_argument("dataset", type=Path, help="directory containing dataset.json")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("enrich", help="add projections and clusterings to a dataset")
    p.add_argument("dataset", type=Path, help="directory containing dataset.json and embeddings")
    p.add_argument("--refit", action="store_true",
                   help="fit the layout afresh instead of placing new ideas into the saved one")
    p.set_defaults(func=cmd_enrich)

    p = sub.add_parser("serve", help="run the local server")
    p.add_argument("dataset", type=Path, help="directory containing dataset.json")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--host", default="127.0.0.1")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
