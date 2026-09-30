"""The local server: the dataset, blind rating sessions, and the built frontend.

`uv run python -m explorer serve <dataset-dir>` then open http://localhost:8765.
In development, `npm run dev` in explorer/web serves the frontend and passes
/api through to this server.
"""

from __future__ import annotations

import copy
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, StrictFloat

from explorer import sessions
from explorer.contract import DATASET_FILE, load_dataset, subset

WEB_DIST = Path(__file__).resolve().parent / "web" / "dist"


class DatasetStore:
    """The dataset, reloaded whenever dataset.json changes on disk."""

    def __init__(self, directory: Path):
        self.directory = directory
        self._mtime: float | None = None
        self._data: dict | None = None

    def get(self) -> dict:
        mtime = (self.directory / DATASET_FILE).stat().st_mtime
        if self._data is None or mtime != self._mtime:
            self._data, self._mtime = load_dataset(self.directory), mtime
        return self._data


class CorrectionIn(BaseModel):
    dims: dict[str, StrictFloat]
    reason: str = Field(min_length=1, max_length=500)


class RatingIn(BaseModel):
    dims: dict[str, StrictFloat]     # a number; text or true/false is refused, not coerced
    recognised: bool = False
    note: str = Field(default="", max_length=2000)


def create_app(dataset_dir: Path, static_dir: Path | None = WEB_DIST) -> FastAPI:
    store = DatasetStore(dataset_dir)
    app = FastAPI(title="Idea Explorer", docs_url="/api/docs", openapi_url="/api/openapi.json")

    @app.exception_handler(sessions.SessionError)
    async def session_error(_: Request, err: sessions.SessionError) -> JSONResponse:
        return JSONResponse({"detail": str(err)}, status_code=err.status)

    @app.get("/api/meta")
    def meta() -> dict:
        """Title, description and session progress. Safe to show before rating."""
        data = store.get()
        m = data["meta"]
        return {"id": m["id"], "title": m["title"], "description": m.get("description", ""),
                "ideas": len(data["ideas"]),
                "sessions": sessions.with_held_back(dataset_dir, data)}

    @app.get("/api/dataset")
    def dataset() -> dict:
        """The dataset for every data view: revealed human ratings merged in as scorings,
        and every idea an unrevealed session holds back left out."""
        data = store.get()
        held = set().union(*sessions.held_back(dataset_dir, data).values())
        human = sessions.human_scorings(dataset_dir, data)
        if held:
            data = subset(data, {i["id"] for i in data["ideas"]} - held)
        if not human:
            return data
        merged = data if held else copy.deepcopy(data)
        for idea in merged["ideas"]:
            for scorer, scoring in human.get(idea["id"], {}).items():
                idea.setdefault("scorings", {})[scorer] = scoring
        return merged

    @app.get("/api/sessions/{session_id}")
    def blind(session_id: str) -> dict:
        return sessions.blind_view(dataset_dir, store.get(), session_id)

    @app.put("/api/sessions/{session_id}/ratings/{slot}")
    def rate(session_id: str, slot: str, body: RatingIn) -> dict:
        return sessions.save_rating(dataset_dir, store.get(), session_id, slot, body.dims,
                                    body.recognised, body.note)

    @app.put("/api/sessions/{session_id}/corrections/{slot}")
    def correct(session_id: str, slot: str, body: CorrectionIn) -> dict:
        return sessions.correct_rating(dataset_dir, store.get(), session_id, slot, body.dims,
                                       body.reason)

    @app.post("/api/sessions/{session_id}/reveal")
    def reveal(session_id: str) -> list[dict]:
        return sessions.reveal(dataset_dir, store.get(), session_id)

    @app.get("/api/sessions/{session_id}/key")
    def key(session_id: str) -> list[dict]:
        return sessions.key(dataset_dir, store.get(), session_id)

    @app.get("/api/{rest:path}", include_in_schema=False)
    def unknown_api(rest: str) -> None:
        raise HTTPException(404, f"no API route /api/{rest}")

    if static_dir is not None and (static_dir / "index.html").exists():
        root = static_dir.resolve()

        @app.get("/{path:path}", include_in_schema=False)
        def frontend(path: str) -> FileResponse:
            """Built files as they are; any other path gets the app, which routes itself."""
            target = (root / path).resolve()
            if path and target.is_file() and target.is_relative_to(root):
                return FileResponse(target)
            return FileResponse(root / "index.html")

    return app
