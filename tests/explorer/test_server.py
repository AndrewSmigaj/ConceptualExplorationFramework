"""The server and its blind rating rules."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from test_contract import minimal

from explorer.server import create_app
from explorer.sessions import RATINGS_DIR

SLOTS = {"a1": "x2", "a2": "x0", "a3": "x1"}
GOOD = {"q": 0.5, "noise": 0.25}


@pytest.fixture
def setup(tmp_path):
    data = minimal()
    (tmp_path / "dataset.json").write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "sessions").mkdir()
    session = {"id": "s1", "items": [{"slot": s, "idea": i, "stratum": f"group-{i}",
                                      "stratum_label": f"Group {i}"} for s, i in SLOTS.items()]}
    (tmp_path / "sessions" / "s1.json").write_text(json.dumps(session), encoding="utf-8")
    return TestClient(create_app(tmp_path, static_dir=None)), tmp_path, data


def rate_all(client, dims=GOOD):
    for slot in SLOTS:
        assert client.put(f"/api/sessions/s1/ratings/{slot}", json={"dims": dims}).status_code == 200


def test_blind_view_holds_nothing_but_slots_and_texts(setup):
    client, _, data = setup
    r = client.get("/api/sessions/s1")
    assert r.status_code == 200
    view = r.json()
    assert set(view) == {"session", "revealed", "context", "rubric", "items", "saved"}
    assert all(set(item) == {"slot", "text"} for item in view["items"])
    assert [i["slot"] for i in view["items"]] == list(SLOTS)
    body = r.text
    idea = data["ideas"][0]
    leaks = [i["id"] for i in data["ideas"]] + ["group-", "Group ", idea["author"],
                                                 idea["essence"], "scorings", "per_scorer"]
    assert not [x for x in leaks if x in body]


def test_meta_lists_progress_without_contents(setup):
    client, _, _ = setup
    rate_all(client)
    m = client.get("/api/meta").json()
    assert m["sessions"] == [{"id": "s1", "total": 3, "rated": 3, "revealed": False,
                              "held_back": 4}]      # x0-x2, plus x3 as x2's duplicate
    assert "x0" not in json.dumps(m)


def test_key_is_locked_until_reveal_and_reveal_needs_every_slot(setup):
    client, _, _ = setup
    assert client.get("/api/sessions/s1/key").status_code == 403
    client.put("/api/sessions/s1/ratings/a1", json={"dims": GOOD})
    r = client.post("/api/sessions/s1/reveal")
    assert r.status_code == 409 and "a2" in r.json()["detail"]
    assert client.get("/api/sessions/s1/key").status_code == 403


@pytest.mark.parametrize("dims", [
    {"q": 0.5},                                # missing a dimension
    {"q": 0.5, "noise": 0.2, "extra": 0.1},    # unknown dimension
    {"q": 1.5, "noise": 0.2},                  # out of range
    {"q": "0.5", "noise": 0.2},                # text is refused, not coerced
    {"q": True, "noise": 0.2},                 # so is true/false
])
def test_bad_ratings_are_refused(setup, dims):
    client, directory, _ = setup
    r = client.put("/api/sessions/s1/ratings/a1", json={"dims": dims})
    assert r.status_code == 422
    assert not (directory / RATINGS_DIR / "s1.jsonl").exists()


def test_unknown_session_slot_and_unsafe_ids(setup):
    client, _, _ = setup
    assert client.get("/api/sessions/nope").status_code == 404
    assert client.get("/api/sessions/..%2Fdataset").status_code == 404
    assert client.put("/api/sessions/s1/ratings/zz", json={"dims": GOOD}).status_code == 404


def test_ratings_append_latest_wins_and_reveal_locks(setup):
    client, directory, _ = setup
    rate_all(client)
    client.put("/api/sessions/s1/ratings/a2", json={"dims": {"q": 0.9, "noise": 0.0},
                                                     "recognised": True, "note": "seen it"})
    log = directory / RATINGS_DIR / "s1.jsonl"
    assert len(log.read_text(encoding="utf-8").splitlines()) == 4     # appended, not rewritten
    saved = client.get("/api/sessions/s1").json()["saved"]
    assert saved["a2"] == {"dims": {"q": 0.9, "noise": 0.0}, "recognised": True, "note": "seen it"}

    key = client.post("/api/sessions/s1/reveal").json()
    assert {k["slot"]: k["idea"] for k in key} == SLOTS
    a2 = next(k for k in key if k["slot"] == "a2")
    assert a2["scorings"]["h"] == {"q": 0.9, "noise": 0.0}
    assert a2["scorings"]["s1"] == {"q": 0.5, "noise": 0.25}
    assert a2["stratum_label"] == "Group x0" and a2["recognised"] is True

    assert client.put("/api/sessions/s1/ratings/a1", json={"dims": GOOD}).status_code == 409
    assert client.get("/api/sessions/s1/key").status_code == 200
    assert client.post("/api/sessions/s1/reveal").status_code == 200    # idempotent
    assert len(log.read_text(encoding="utf-8").splitlines()) == 4


def test_unrevealed_session_ideas_and_duplicates_are_held_back(setup):
    client, _, _ = setup
    rate_all(client)
    before = client.get("/api/dataset").json()
    assert before["ideas"] == []                    # all four are held back
    client.post("/api/sessions/s1/reveal")
    after = client.get("/api/dataset").json()
    assert {i["id"] for i in after["ideas"]} == {"x0", "x1", "x2", "x3"}


def test_dataset_gains_human_scorings_only_after_reveal(setup):
    client, _, _ = setup
    rate_all(client)
    client.post("/api/sessions/s1/reveal")
    after = {i["id"]: i["scorings"] for i in client.get("/api/dataset").json()["ideas"]}
    assert all(after[i]["h"]["dims"] == GOOD for i in SLOTS.values())
    assert "h" not in after["x3"]


def test_frontend_is_served_with_app_routing(tmp_path):
    data_dir, dist = tmp_path / "d", tmp_path / "dist"
    data_dir.mkdir()
    (data_dir / "dataset.json").write_text(json.dumps(minimal()), encoding="utf-8")
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    client = TestClient(create_app(data_dir, static_dir=dist))
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/rate/s1").text == "<html>app</html>"
    assert client.get("/api/nothing").status_code == 404


def write_session(directory, items):
    (directory / "sessions" / "s2.json").write_text(json.dumps({"id": "s2", "items": items}),
                                                    encoding="utf-8")


def test_silent_repeats_count_once_and_are_marked_in_the_key(setup):
    client, directory, _ = setup
    (directory / "sessions" / "s1.json").unlink()     # its hold-back would hide x0
    write_session(directory, [{"slot": "b1", "idea": "x0"}, {"slot": "b2", "idea": "x1"},
                              {"slot": "b3", "idea": "x0", "repeat_of": "b1"}])
    view = client.get("/api/sessions/s2").json()
    assert "repeat" not in json.dumps(view)                     # silent to the rater
    for slot, q in (("b1", 0.2), ("b2", 0.5), ("b3", 0.8)):
        client.put(f"/api/sessions/s2/ratings/{slot}", json={"dims": {"q": q, "noise": 0.0}})
    key = {k["slot"]: k for k in client.post("/api/sessions/s2/reveal").json()}
    assert key["b3"]["repeat_of"] == "b1" and key["b1"]["repeat_of"] is None
    scorings = {i["id"]: i["scorings"] for i in client.get("/api/dataset").json()["ideas"]}
    assert scorings["x0"]["h"]["dims"]["q"] == 0.2              # first exposure is of record


@pytest.mark.parametrize("items", [
    [{"slot": "b1", "idea": "x0"}, {"slot": "b2", "idea": "x0"}],                     # unmarked
    [{"slot": "b1", "idea": "x0", "repeat_of": "b2"}, {"slot": "b2", "idea": "x0"}],  # backwards
    [{"slot": "b1", "idea": "x0"}, {"slot": "b2", "idea": "x1", "repeat_of": "b1"}],  # wrong idea
])
def test_malformed_repeats_are_refused(setup, items):
    client, directory, _ = setup
    write_session(directory, items)
    assert client.get("/api/sessions/s2").status_code == 500


def test_typo_corrections_only_after_reveal_with_a_reason(setup):
    client, directory, _ = setup
    rate_all(client)
    fix = {"dims": {"q": 0.9, "noise": 0.25}, "reason": "typed 0.5 for 0.9"}
    assert client.put("/api/sessions/s1/corrections/a1", json=fix).status_code == 409
    client.post("/api/sessions/s1/reveal")
    assert client.put("/api/sessions/s1/corrections/a1",
                      json={**fix, "reason": "  "}).status_code == 422
    assert client.put("/api/sessions/s1/corrections/a1",
                      json={**fix, "reason": ""}).status_code == 422
    r = client.put("/api/sessions/s1/corrections/a1", json=fix)
    assert r.status_code == 200 and r.json()["correction"]["replaces"] == GOOD
    log = directory / RATINGS_DIR / "s1.jsonl"
    assert len(log.read_text(encoding="utf-8").splitlines()) == 4     # the original stays
    key = {k["slot"]: k for k in client.get("/api/sessions/s1/key").json()}
    assert key["a1"]["scorings"]["h"]["q"] == 0.9
    assert key["a1"]["correction"]["reason"] == "typed 0.5 for 0.9"
    scoring = {i["id"]: i["scorings"] for i in client.get("/api/dataset").json()["ideas"]}["x2"]["h"]
    assert scoring["dims"]["q"] == 0.9 and scoring["flags"] == ["corrected after reveal"]
    # Ordinary rating stays locked after the reveal.
    assert client.put("/api/sessions/s1/ratings/a1", json={"dims": GOOD}).status_code == 409
