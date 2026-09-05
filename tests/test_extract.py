"""Unit tests for the OATutor extractor.

Run: python -m pytest tests/ -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oatutor_extract.extract import (  # noqa: E402
    norm_text,
    content_signature,
    find_figures,
    order_solution,
    parse_tutoring_item,
    linearize_solution,
)


def test_norm_text_literal_newline():
    assert norm_text("a\\nb") == "a\nb"
    assert norm_text("x   y") == "x y"
    assert norm_text(None) == ""
    assert norm_text("keep $$\\frac{1}{2}$$") == "keep $$\\frac{1}{2}$$"


def test_find_figures():
    refs, missing = find_figures("see ##figure1.gif## and ##figure2.gif##", {"figure1.gif"})
    assert refs == ["figure1.gif", "figure2.gif"]
    assert missing == ["figure2.gif"]


def test_content_signature_stable_and_distinct():
    a = [{"question": "x+y=1", "answer": ["1"]}]
    b = [{"question": "x+y=1", "answer": ["1"]}]
    c = [{"question": "x+y=2", "answer": ["2"]}]
    assert content_signature(a) == content_signature(b)
    assert content_signature(a) != content_signature(c)


def test_order_solution_topological():
    nodes = [
        {"id": "h2", "depends_on": ["h1"], "text": "", "type": "hint", "children": []},
        {"id": "h1", "depends_on": [], "text": "", "type": "hint", "children": []},
        {"id": "h3", "depends_on": ["h2"], "text": "", "type": "hint", "children": []},
    ]
    ordered, cycle = order_solution(nodes)
    assert [n["id"] for n in ordered] == ["h1", "h2", "h3"]
    assert cycle is False


def test_order_solution_dangling_ref_is_lossless():
    # A dep on an id not among the top-level nodes (e.g. a nested subHint id) is
    # ignored: ordering still completes and nothing is dropped.
    nodes = [
        {"id": "h1", "depends_on": ["missing"], "text": "", "type": "hint", "children": []},
        {"id": "h2", "depends_on": ["h1"], "text": "", "type": "hint", "children": []},
    ]
    ordered, cycle = order_solution(nodes)
    assert [n["id"] for n in ordered] == ["h1", "h2"]
    assert cycle is False


def test_order_solution_true_cycle_keeps_all():
    nodes = [
        {"id": "h1", "depends_on": ["h2"], "text": "", "type": "hint", "children": []},
        {"id": "h2", "depends_on": ["h1"], "text": "", "type": "hint", "children": []},
    ]
    ordered, cycle = order_solution(nodes)
    assert len(ordered) == 2          # nothing dropped even on a cycle
    assert cycle is True


def test_parse_tutoring_recursion_and_scaffold():
    item = {
        "id": "s1", "type": "scaffold", "dependencies": [],
        "title": "T", "text": "what is 2+2? ##figure1.gif##",
        "problemType": "TextBox", "answerType": "arithmetic",
        "hintAnswer": ["$$4$$"],
        "subHints": [{"id": "s1-1", "type": "hint", "dependencies": [],
                      "title": "sub", "text": "add them"}],
    }
    missing = []
    node = parse_tutoring_item(item, {"figure1.gif"}, missing)
    assert node["type"] == "scaffold"
    assert node["scaffold_answer"] == ["$$4$$"]
    assert len(node["children"]) == 1
    assert node["children"][0]["id"] == "s1-1"


def test_linearize_includes_scaffold_answer():
    sol = [{"id": "s1", "type": "scaffold", "title": "Q", "text": "solve",
            "scaffold_answer": ["$$4$$"], "children": []}]
    out = linearize_solution(sol)
    assert "solve" in out and "$$4$$" in out
