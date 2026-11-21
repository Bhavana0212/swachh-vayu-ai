"""Smoke tests: the app and package import and wire up correctly.

Streamlit pages need a running server to render, so these tests check the
static wiring instead: the app file compiles, the page list matches the
renderer map, and every planner module imports cleanly.
"""
import ast
import importlib
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_app_file_compiles():
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    assert tree is not None


def test_app_pages_match_renderers():
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    pages = None
    renderers = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            name = getattr(node.targets[0], "id", "")
            if name == "PAGES" and isinstance(node.value, ast.List):
                # PAGES is a list of (i18n key, page id) tuples.
                pages = [elt.elts[1].value for elt in node.value.elts]
            if name == "ROUTER" and isinstance(node.value, ast.Dict):
                renderers = [k.value for k in node.value.keys]
    assert pages, "PAGES not found in app.py"
    assert renderers, "ROUTER not found in app.py"
    assert pages == renderers
    assert len(pages) == 18  # one page per spec module


def test_app_declares_expected_pages():
    source = APP_PATH.read_text(encoding="utf-8")
    for page in ("home", "locations", "forecast", "routine", "activity",
                 "indoor", "alternatives", "whatif", "ai", "compare",
                 "alerts", "family", "equipment", "awareness", "community",
                 "analytics", "plan", "learn"):
        assert f'"{page}"' in source
    assert "SwachhVayu AI" in source


def test_planner_modules_import():
    for module in ("aqi", "api", "routine", "indoor", "alternatives",
                   "ai", "export", "utils", "why", "safety", "whatif",
                   "score", "household", "habits", "alerts", "indian_aqi",
                   "store", "i18n", "forecast", "rooms", "voice", "twin",
                   "awareness", "community", "school"):
        importlib.import_module(f"planner.{module}")


def test_no_hardcoded_api_key_in_source():
    root = Path(__file__).resolve().parents[1]
    # Scan shipped code only (not this test file, which names the pattern).
    paths = [root / "app.py"] + list((root / "planner").glob("*.py")) \
        + [root / "README.md"]
    marker = "AI" + "za"  # Google key prefix, built to avoid self-matching
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert marker not in text, f"possible hard-coded key in {path}"
