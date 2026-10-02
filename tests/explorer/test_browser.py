"""The built explorer, driven in headless Chromium against a synthetic dataset.

Opt-in: `uv run pytest -m browser`. Needs the frontend built (`npm run build` in
explorer/web) and Playwright's Chromium (`uv run playwright install chromium`).
No real idea content is used; the dataset is generated here.
"""

from __future__ import annotations

import json
import re
import socket
import threading
import time

import numpy as np
import pytest

pytestmark = pytest.mark.browser

playwright_api = pytest.importorskip("playwright.sync_api")

from explorer.server import WEB_DIST, create_app

GROUPS = ["alpha", "beta", "gamma", "delta"]


def synthetic(directory) -> dict:
    """60 ideas in four groups, two model scorers and a human, every chart kind."""
    rng = np.random.default_rng(3)
    ideas = []
    for n in range(60):
        g = GROUPS[n % 4]
        ideas.append({
            "id": f"x{n:02d}",
            "text": f"Synthetic idea {n} from the {g} group, written to test the page.",
            "essence": f"Essence of synthetic idea {n}.",
            "author": "gen-a" if n % 2 else "gen-b",
            "parents": ["x00"] if n % 4 == 1 and n > 1 else [],
            "run": f"run-{g}",
            "facets": {"group": g},
            "metrics": {"size": float(20 + n % 17), "round": 1 + n % 3},
            "per_scorer": {s: {"level": 1 + (n + k) % 3, "gap": round(float(rng.random()), 3)}
                           for k, s in enumerate(("s1", "s2"))},
            "scorings": {s: {"dims": {"q": round(float(rng.random()), 2),
                                      "noise": round(float(rng.random()), 2)}}
                         for s in ("s1", "s2")},
        })
    coords = {d: {i["id"]: [round(float(x), 3) for x in rng.normal(size=d)] for i in ideas}
              for d in (2, 3)}
    data = {
        "schema_version": 1,
        "meta": {
            "id": "synthetic", "title": "Synthetic ideas", "generated_at": "2026-09-27T00:00:00Z",
            "producer": "tests/explorer/test_browser.py",
            "context": [{"id": "problem", "title": "The problem", "text": "A problem statement."}],
            "rubric": {"id": "r", "sha256": "0" * 64, "text": "Rate it.", "dimensions": [
                {"id": "q", "label": "Quality", "min": 0, "max": 1, "direction": "higher",
                 "headline": True, "description": "How good it is."},
                {"id": "noise", "label": "Noise", "min": 0, "max": 1, "direction": "lower"},
            ]},
        },
        "scorers": [{"id": "s1", "label": "Scorer A", "kind": "model", "generator": "gen-a"},
                    {"id": "s2", "label": "Scorer B", "kind": "model", "generator": "gen-b"},
                    {"id": "h", "label": "Human", "kind": "human"}],
        "generators": [{"id": "gen-a", "label": "Generator A"}, {"id": "gen-b", "label": "Generator B"}],
        "fields": [
            {"id": "group", "label": "Group", "kind": "facet",
             "values": [{"id": g, "label": g.title()} for g in GROUPS]},
            {"id": "size", "label": "Size", "kind": "metric"},
            {"id": "round", "label": "Round", "kind": "metric", "sequence": True},
            {"id": "level", "label": "Level", "kind": "facet", "per_scorer": True, "ordered": True,
             "values": [{"id": k, "label": f"Level {k}", "description": f"Level {k} explained."}
                        for k in (1, 2, 3)]},
            {"id": "gap", "label": "Gap", "kind": "metric", "per_scorer": True},
        ],
        "ideas": ideas,
        "runs": [{"id": f"run-{g}", "label": f"Run {g}", "status": "done", "author": "gen-a",
                  "facets": {"group": g}, "counts": {"generated": 15, "rounds": 3}} for g in GROUPS],
        "edge_kinds": [{"id": "dup", "label": "Same point", "duplicate": True}],
        "edges": [{"kind": "dup", "source": "x10", "target": "x11", "note": "Synthetic."}],
        "presets": [
            {"id": "p-cloud", "title": "Cloud", "kind": "projection",
             "spec": {"projections": ["umap3d", "umap2d"], "scorers": ["s1", "s2"],
                      "color": {"per_scorer": "level"}}},
            {"id": "p-table", "title": "Counts", "kind": "table",
             "spec": {"rows": {"field": "group"},
                      "columns": [{"kind": "count"},
                                  {"kind": "per_scorer_counts", "per_scorer": "level",
                                   "scorers": ["s1", "s2"]}]}},
            {"id": "p-scatter", "title": "Scatter", "kind": "scatter",
             "spec": {"panels": ["s1", "s2"], "x": [{"per_scorer": "gap"}], "y": [{"dim": "q"}],
                      "split": "author", "bins": 4}},
            {"id": "p-paired", "title": "Paired", "kind": "paired",
             "spec": {"panels": ["s1", "s2"], "reference": "h", "x": {"per_scorer": "level"},
                      "y": [{"dim": "q"}]}},
        ],
        "projections": {
            "umap3d": {"method": "umap", "dims": 3, "coords": coords[3]},
            "umap2d": {"method": "umap", "dims": 2, "coords": coords[2]},
        },
    }
    (directory / "dataset.json").write_text(json.dumps(data), encoding="utf-8")
    (directory / "sessions").mkdir()
    session = {"id": "s1", "items": [{"slot": f"a{k}", "idea": f"x{k:02d}", "stratum": "g",
                                      "stratum_label": "Group label"} for k in range(4)]}
    (directory / "sessions" / "s1.json").write_text(json.dumps(session), encoding="utf-8")
    return data


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    if not (WEB_DIST / "index.html").exists():
        pytest.skip("frontend not built: cd explorer/web && npm run build")
    import uvicorn

    directory = tmp_path_factory.mktemp("browser")
    data = synthetic(directory)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(create_app(directory), host="127.0.0.1", port=port,
                                        log_level="warning"))
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}", data
    srv.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def page(server):
    try:
        with playwright_api.sync_playwright() as p:
            browser = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-webgl",
                                              "--ignore-gpu-blocklist"])
            pg = browser.new_page(viewport={"width": 1500, "height": 1000})
            errors: list[str] = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.on("dialog", lambda d: d.accept())
            yield pg, errors, server[0], server[1]
            browser.close()
    except playwright_api.Error as err:
        if "Executable doesn't exist" in str(err):
            pytest.skip("Chromium not installed: uv run playwright install chromium")
        raise


def test_rating_is_blind_then_reveals(page):
    pg, errors, base, data = page
    pg.goto(f"{base}/#/rate/s1")
    pg.wait_for_selector("text=Item 1 of 4")
    html = pg.content()
    assert not any(i["id"] in html for i in data["ideas"]), "an idea id reached the rating page"
    pg.locator("input[type=number]").first.focus()
    for n in range(4):
        pg.wait_for_selector(f"text=Item {n + 1} of 4")
        for _ in range(2):                       # two dimensions: type, Enter
            pg.keyboard.type("0.5")
            pg.keyboard.press("Enter")
        pg.wait_for_selector(f"text={n + 1} of 4 saved")
    pg.click("button:has-text('Finish and reveal')")
    pg.click("button:has-text('Reveal now')")
    pg.wait_for_selector("text=Results")
    # The rows render after the heading, so wait for them rather than counting at once.
    pg.wait_for_selector("text=Group label")
    assert not errors


@pytest.mark.parametrize("preset", ["p-cloud", "p-table", "p-scatter", "p-paired"])
def test_every_figure_kind_renders(page, preset):
    pg, errors, base, _ = page
    pg.goto(f"{base}/#/figures/{preset}")
    pg.wait_for_selector("section.figure h1")
    pg.wait_for_timeout(1500)
    assert pg.locator(".plot, table.data, p.note").count() >= 1
    assert not errors


def test_explore_layers_growth_and_details(page):
    pg, errors, base, _ = page
    pg.goto(f"{base}/#/explore")
    pg.wait_for_selector("text=ideas shown")
    def shown() -> int:
        return int(re.search(r"(\d+) of 60 ideas shown", pg.locator("p.count").inner_text())[1])

    pg.click("button:has-text('First only')")
    pg.wait_for_timeout(300)
    assert shown() == 15                          # one group of four
    pg.click("button:has-text('Add next')")
    pg.wait_for_timeout(300)
    assert shown() == 30
    pg.locator("input[type=range]").fill("1")     # growth: round 1 only
    pg.wait_for_timeout(300)
    assert shown() == 10
    pg.click("button:has-text('All')")
    pg.locator("input[type=range]").fill("3")
    pg.click(".side button:has-text('2D')")
    pg.wait_for_timeout(1500)
    box = pg.locator(".scatterlayer .point").nth(5).bounding_box()
    pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    pg.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    pg.wait_for_selector("aside.panel")
    assert not errors


def test_table_sorts_and_runs_reconcile(page):
    pg, errors, base, _ = page
    pg.goto(f"{base}/#/table")
    pg.wait_for_selector("table.data tbody tr")
    before = pg.locator("table.data tbody tr").first.inner_text()
    pg.locator("th button.sort", has_text="Quality · Scorer A").click()
    pg.wait_for_timeout(300)
    assert pg.locator("table.data tbody tr").first.inner_text() != before
    pg.goto(f"{base}/#/runs")
    pg.wait_for_selector("text=Every run")
    assert pg.locator("p.check:not(.bad)").count() == 1
    assert not errors
