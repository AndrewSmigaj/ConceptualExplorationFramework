"""Blind rating sessions: the rules the server enforces.

A session is defined by the dataset's producer in <dataset>/sessions/<id>.json:
  {"id", "items": [{"slot", "idea", "stratum"?, "stratum_label"?, "repeat_of"?}],
   "rubric_sha256"?, "scorer"?}
It is the key: which idea sits in which slot. The rater never sees it until the
session is revealed.

An idea may appear in a second slot only as a silent repeat: that item names
the earlier slot in `repeat_of`. Repeats measure the rater's own consistency;
only the first exposure becomes the rater's scoring of the idea.

Ratings are appended to <dataset>/annotations/ratings/<id>.jsonl; the latest
record for a slot wins, and nothing is ever rewritten. Revealing requires every
slot rated, writes <id>.revealed.json, and locks the session. Only revealed
ratings join the dataset as the human scorer's scorings.

After the reveal the only change allowed is a typo correction: it needs a
reason, is appended like any rating with the value it replaces, and is flagged
wherever it is used, because it was made with the answers in view.

Blindness is structural: `blind_view` returns the context, the rubric and
{slot, text} per item, and nothing that identifies an idea or where it came from.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
from pathlib import Path

SESSIONS_DIR = "sessions"
RATINGS_DIR = Path("annotations") / "ratings"
SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class SessionError(Exception):
    """A request the session rules refuse. `status` is the HTTP status to report."""

    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def _paths(directory: Path, session_id: str) -> tuple[Path, Path, Path]:
    if not SESSION_ID.match(session_id):
        raise SessionError(404, f"no session {session_id!r}")
    ratings = directory / RATINGS_DIR
    return (directory / SESSIONS_DIR / f"{session_id}.json",
            ratings / f"{session_id}.jsonl",
            ratings / f"{session_id}.revealed.json")


def load_session(directory: Path, data: dict, session_id: str) -> dict:
    definition, _, _ = _paths(directory, session_id)
    if not definition.exists():
        raise SessionError(404, f"no session {session_id!r}")
    session = json.loads(definition.read_text(encoding="utf-8"))
    ideas = {i["id"] for i in data["ideas"]}
    slots = [item["slot"] for item in session["items"]]
    problems = []
    if session.get("id") != session_id:
        problems.append("its id does not match its file name")
    if len(set(slots)) != len(slots):
        problems.append("slots repeat")
    first_slot: dict[str, str] = {}
    for item in session["items"]:
        earlier = first_slot.get(item["idea"])
        if earlier is None:
            if "repeat_of" in item:
                problems.append(f"slot {item['slot']} repeats an idea not shown earlier")
            first_slot[item["idea"]] = item["slot"]
        elif item.get("repeat_of") != earlier:
            problems.append(f"slot {item['slot']} shows an idea again without "
                            f"repeat_of={earlier!r}")
    if any(item["idea"] not in ideas for item in session["items"]):
        problems.append("an item names an idea not in the dataset")
    rubric = data["meta"].get("rubric")
    if not rubric:
        problems.append("the dataset declares no rubric")
    elif session.get("rubric_sha256") not in (None, rubric.get("sha256")):
        problems.append("it was drawn against a different rubric")
    if problems:
        raise SessionError(500, f"session {session_id!r} is invalid: " + "; ".join(problems))
    return session


def human_scorer(data: dict, session: dict) -> str:
    if "scorer" in session:
        return session["scorer"]
    humans = [s["id"] for s in data["scorers"] if s["kind"] == "human"]
    if len(humans) != 1:
        raise SessionError(500, "the session names no scorer and the dataset does not declare "
                                "exactly one human scorer")
    return humans[0]


def ratings(directory: Path, session_id: str) -> dict[str, dict]:
    """The latest rating per slot."""
    _, log, _ = _paths(directory, session_id)
    latest: dict[str, dict] = {}
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                latest[record["slot"]] = record
    return latest


def revealed(directory: Path, session_id: str) -> bool:
    return _paths(directory, session_id)[2].exists()


def summary(directory: Path, data: dict) -> list[dict]:
    """Every session with its progress. No contents."""
    folder = directory / SESSIONS_DIR
    out = []
    for path in sorted(folder.glob("*.json")) if folder.exists() else []:
        session = load_session(directory, data, path.stem)
        out.append({"id": session["id"], "total": len(session["items"]),
                    "rated": len(ratings(directory, session["id"])),
                    "revealed": revealed(directory, session["id"])})
    return out


def with_held_back(directory: Path, data: dict) -> list[dict]:
    """`summary`, plus how many ideas each unrevealed session holds back."""
    held = held_back(directory, data)
    return [{**s, "held_back": len(held.get(s["id"], ()))} for s in summary(directory, data)]


def blind_view(directory: Path, data: dict, session_id: str) -> dict:
    """What the rater may see: context, rubric, and {slot, text}. Nothing else."""
    session = load_session(directory, data, session_id)
    texts = {i["id"]: i["text"] for i in data["ideas"]}
    rubric = data["meta"]["rubric"]
    saved = ratings(directory, session_id)
    return {
        "session": session_id,
        "revealed": revealed(directory, session_id),
        "context": data["meta"].get("context", []),
        "rubric": {"text": rubric["text"],
                   "dimensions": [{k: d[k] for k in ("id", "label", "description", "min", "max")
                                   if k in d} for d in rubric["dimensions"]]},
        "items": [{"slot": item["slot"], "text": texts[item["idea"]]}
                  for item in session["items"]],
        "saved": {slot: {k: r[k] for k in ("dims", "recognised", "note")}
                  for slot, r in saved.items()},
    }


def _checked_dims(data: dict, dims: dict) -> dict:
    rubric = {d["id"]: d for d in data["meta"]["rubric"]["dimensions"]}
    if set(dims) != set(rubric):
        raise SessionError(422, f"expected exactly the dimensions {sorted(rubric)}")
    for k, v in dims.items():
        d = rubric[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not d["min"] <= v <= d["max"]:
            raise SessionError(422, f"{k} must be a number from {d['min']} to {d['max']}")
    return {k: float(dims[k]) for k in rubric}


def _item(session: dict, session_id: str, slot: str) -> dict:
    item = next((i for i in session["items"] if i["slot"] == slot), None)
    if item is None:
        raise SessionError(404, f"no slot {slot!r} in session {session_id!r}")
    return item


def _append(directory: Path, session_id: str, record: dict) -> None:
    _, log, _ = _paths(directory, session_id)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_rating(directory: Path, data: dict, session_id: str, slot: str, dims: dict,
                recognised: bool = False, note: str = "") -> dict:
    session = load_session(directory, data, session_id)
    if revealed(directory, session_id):
        raise SessionError(409, "this session has been revealed; its ratings are locked")
    item = _item(session, session_id, slot)
    record = {"slot": slot, "idea": item["idea"], "dims": _checked_dims(data, dims),
              "recognised": bool(recognised), "note": note, "at": _now()}
    _append(directory, session_id, record)
    return {k: record[k] for k in ("slot", "dims", "recognised", "note", "at")}


def correct_rating(directory: Path, data: dict, session_id: str, slot: str, dims: dict,
                   reason: str) -> dict:
    """Fix a typo after the reveal. The reason is required and the replaced value kept."""
    session = load_session(directory, data, session_id)
    if not revealed(directory, session_id):
        raise SessionError(409, "before the reveal, change the rating itself; corrections "
                                "are for revealed sessions")
    if not reason.strip():
        raise SessionError(422, "a correction needs a reason")
    _item(session, session_id, slot)
    previous = ratings(directory, session_id)[slot]
    record = {**{k: previous[k] for k in ("slot", "idea", "recognised", "note")},
              "dims": _checked_dims(data, dims), "at": _now(),
              "correction": {"reason": reason.strip(), "after_reveal": True,
                             "replaces": previous["dims"], "replaces_at": previous["at"]}}
    _append(directory, session_id, record)
    return {k: record[k] for k in ("slot", "dims", "at", "correction")}


def reveal(directory: Path, data: dict, session_id: str) -> list[dict]:
    session = load_session(directory, data, session_id)
    if not revealed(directory, session_id):
        missing = [i["slot"] for i in session["items"]
                   if i["slot"] not in ratings(directory, session_id)]
        if missing:
            raise SessionError(409, f"rate every slot first; missing {missing}")
        _, log, marker = _paths(directory, session_id)
        marker.write_text(json.dumps({
            "revealed_at": _now(),
            "ratings_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        }, indent=1) + "\n", encoding="utf-8")
    return key(directory, data, session_id)


def key(directory: Path, data: dict, session_id: str) -> list[dict]:
    """Every slot with its idea, stratum, the human rating and every scorer's scoring."""
    session = load_session(directory, data, session_id)
    if not revealed(directory, session_id):
        raise SessionError(403, "the key is available only after the session is revealed")
    ideas = {i["id"]: i for i in data["ideas"]}
    saved = ratings(directory, session_id)
    scorer = human_scorer(data, session)
    out = []
    for item in session["items"]:
        idea = ideas[item["idea"]]
        rating = saved[item["slot"]]
        scorings = {s: v["dims"] for s, v in idea.get("scorings", {}).items()}
        scorings[scorer] = rating["dims"]
        out.append({"slot": item["slot"], "idea": idea["id"], "text": idea["text"],
                    "repeat_of": item.get("repeat_of"),
                    "stratum": item.get("stratum"), "stratum_label": item.get("stratum_label"),
                    "author": idea.get("author"), "facets": idea.get("facets", {}),
                    "per_scorer": idea.get("per_scorer", {}), "scorings": scorings,
                    "human_scorer": scorer, "recognised": rating["recognised"],
                    "note": rating["note"], "correction": rating.get("correction")})
    return out


def held_back(directory: Path, data: dict) -> dict[str, set[str]]:
    """Ideas withheld from every data view until their session is revealed.

    {session id: idea ids}: each unrevealed session's ideas, plus every idea
    joined to one of them by an edge kind the dataset declares a duplicate.
    Seeing a duplicate's provenance or scores would give the blind item away.
    """
    duplicate_kinds = {k["id"] for k in data.get("edge_kinds", []) if k.get("duplicate")}
    partners: dict[str, set[str]] = {}
    for e in data.get("edges", []):
        if e["kind"] in duplicate_kinds:
            partners.setdefault(e["source"], set()).add(e["target"])
            partners.setdefault(e["target"], set()).add(e["source"])
    out = {}
    for s in summary(directory, data):
        if s["revealed"]:
            continue
        ids = {i["idea"] for i in load_session(directory, data, s["id"])["items"]}
        out[s["id"]] = ids | {p for i in ids for p in partners.get(i, ())}
    return out


def human_scorings(directory: Path, data: dict) -> dict[str, dict[str, dict]]:
    """Revealed ratings as scorings: {idea id: {scorer: {"dims", "ref"}}}.

    Repeats are left out: the first exposure is the rating of record.
    """
    out: dict[str, dict[str, dict]] = {}
    for s in summary(directory, data):
        if not s["revealed"]:
            continue
        session = load_session(directory, data, s["id"])
        scorer = human_scorer(data, session)
        repeats = {i["slot"] for i in session["items"] if "repeat_of" in i}
        for slot, r in ratings(directory, s["id"]).items():
            if slot in repeats:
                continue
            scoring = {"dims": r["dims"], "ref": f"session {s['id']}, slot {slot}"}
            if r.get("correction"):
                scoring["flags"] = ["corrected after reveal"]
                scoring["note"] = f"Corrected after reveal: {r['correction']['reason']}"
            out.setdefault(r["idea"], {})[scorer] = scoring
    return out
