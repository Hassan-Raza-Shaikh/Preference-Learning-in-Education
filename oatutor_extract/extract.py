#!/usr/bin/env python3
"""OATutor-Content -> clean ML dataset extractor.

Deterministic, fail-soft, commit-pinned. Reads a local clone of CAHLR/OATutor-Content
and emits a canonical problem-centric JSONL dataset plus provenance/quality side files.

Usage:
    python -m oatutor_extract.extract --content-root /path/to/OATutor-Content --out-dir data
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

from .taxonomy import derive_taxonomy

SCHEMA_VERSION = "1.0"
FIGURE_TOKEN = re.compile(r"##([\w./-]+?\.gif)##")

log = logging.getLogger("oatutor")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def norm_text(s):
    """Whitespace normalization; keeps LaTeX ($$...$$) intact.

    The source stores line breaks inconsistently: some fields use real newlines,
    others embed the literal two-character sequence ``\\n``. Both are unified to
    real newlines so downstream text is consistent.
    """
    if s is None:
        return ""
    s = str(s).replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\\n", "\n")           # literal backslash-n -> newline
    s = re.sub(r"[ \t]+", " ", s)        # collapse spaces/tabs, keep newlines
    s = re.sub(r"\n{3,}", "\n\n", s)     # cap blank-line runs
    return s.strip()


def content_signature(steps):
    """Stable hash of a problem's step questions+answers, for dedup."""
    parts = []
    for st in steps:
        q = re.sub(r"\s+", " ", (st["question"] or "").strip().lower())
        a = re.sub(r"\s+", " ", (str(st["answer"]) or "").strip().lower())
        parts.append(q + "|" + a)
    return hashlib.md5("||".join(parts).encode("utf-8")).hexdigest()


def find_figures(text, available):
    """Return (figure_names_referenced, missing_names) for a text field."""
    refs = FIGURE_TOKEN.findall(text or "")
    missing = [r for r in refs if os.path.basename(r) not in available]
    return refs, missing


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _iter_solution_text(nodes):
    for n in nodes:
        yield n.get("text")
        for a in (n.get("scaffold_answer") or []):
            yield a
        yield from _iter_solution_text(n.get("children") or [])


def _iter_record_text(p_title, p_body, steps):
    yield p_title
    yield p_body
    for st in steps:
        yield st["question"]
        for a in (st["answer"] or []):
            yield a
        yield st.get("answer_latex")
        yield from _iter_solution_text(st["solution"])


# --------------------------------------------------------------------------- #
# tutoring tree
# --------------------------------------------------------------------------- #
def parse_tutoring_item(item, available_figures, missing_acc):
    """Normalize one hint/scaffold item, recursing into subHints."""
    text = norm_text(item.get("text"))
    _, missing = find_figures(text, available_figures)
    missing_acc.extend(missing)
    node = {
        "id": item.get("id"),
        "type": item.get("type"),                     # hint | scaffold
        "depends_on": item.get("dependencies", []) or [],
        "title": norm_text(item.get("title")),
        "text": text,
        "scaffold_answer": item.get("hintAnswer") if item.get("type") == "scaffold" else None,
        "scaffold_problem_type": item.get("problemType") if item.get("type") == "scaffold" else None,
        "scaffold_answer_type": item.get("answerType") if item.get("type") == "scaffold" else None,
        "scaffold_choices": item.get("choices") if item.get("type") == "scaffold" else None,
        "children": [
            parse_tutoring_item(c, available_figures, missing_acc)
            for c in (item.get("subHints") or [])
        ],
    }
    return node


def order_solution(nodes):
    """Topologically order tutoring nodes by their `depends_on` edges.

    Falls back to original order on cycles or dangling refs (recorded by caller
    via the returned `had_cycle` flag).
    """
    by_id = {n["id"]: n for n in nodes}
    indeg = {n["id"]: 0 for n in nodes}
    for n in nodes:
        for d in n["depends_on"]:
            if d in indeg:
                indeg[n["id"]] += 1
    # Kahn's algorithm, preserving original order among ready nodes
    ready = [n["id"] for n in nodes if indeg[n["id"]] == 0]
    ordered, seen = [], set()
    while ready:
        nid = ready.pop(0)
        if nid in seen:
            continue
        seen.add(nid)
        ordered.append(by_id[nid])
        for m in nodes:
            if nid in m["depends_on"] and m["id"] not in seen:
                indeg[m["id"]] -= 1
                if indeg[m["id"]] == 0:
                    ready.append(m["id"])
    had_cycle = len(ordered) != len(nodes)
    if had_cycle:
        # append leftovers in original order so nothing is lost
        for n in nodes:
            if n["id"] not in seen:
                ordered.append(n)
    return ordered, had_cycle


# --------------------------------------------------------------------------- #
# per-problem extraction
# --------------------------------------------------------------------------- #
def extract_problem(problem_dir, skill_model):
    """Return (record | None, list_of_flags, error | None)."""
    pid = os.path.basename(problem_dir)
    pj = os.path.join(problem_dir, pid + ".json")
    if not os.path.exists(pj):
        return None, [], "missing_problem_json"
    try:
        p = load_json(pj)
    except Exception as e:  # noqa: BLE001
        return None, [], f"bad_problem_json:{e}"

    flags = []
    figures_dir = os.path.join(problem_dir, "figures")
    available_figures = (
        {f for f in os.listdir(figures_dir)} if os.path.isdir(figures_dir) else set()
    )
    missing_figs = []

    # ---- problem-level figures ----
    p_title = norm_text(p.get("title"))
    p_body = norm_text(p.get("body"))
    for fld in (p_title, p_body):
        _, miss = find_figures(fld, available_figures)
        missing_figs.extend(miss)
    if not p_title and not p_body:
        flags.append("empty_problem_stem")

    # ---- steps ----
    steps_root = os.path.join(problem_dir, "steps")
    step_dirs = (
        sorted(d for d in (os.path.join(steps_root, x) for x in os.listdir(steps_root))
               if os.path.isdir(d))
        if os.path.isdir(steps_root) else []
    )
    steps = []
    skills = set()
    had_cycle = False
    for order, sdir in enumerate(step_dirs):
        sid = os.path.basename(sdir)
        sj = os.path.join(sdir, sid + ".json")
        if not os.path.exists(sj):
            continue
        try:
            s = load_json(sj)
        except Exception:  # noqa: BLE001
            flags.append("bad_step_json")
            continue

        q = norm_text(s.get("stepTitle"))
        sbody = norm_text(s.get("stepBody"))
        if not q and not sbody:
            flags.append("empty_question")
        question = q or sbody
        _, miss = find_figures(question, available_figures)
        missing_figs.extend(miss)

        answer = s.get("stepAnswer") or []
        if not answer or all(not str(x).strip() for x in answer):
            flags.append("missing_answer")

        ptype = s.get("problemType")
        choices = s.get("choices")
        if ptype == "MultipleChoice" and not choices:
            flags.append("mc_without_choices")

        for sk in skill_model.get(sid, []):
            skills.add(sk)

        # tutoring
        tut_path = os.path.join(sdir, "tutoring", sid + "DefaultPathway.json")
        solution = []
        if not os.path.exists(tut_path):
            flags.append("missing_tutoring")
        else:
            try:
                raw = load_json(tut_path)
            except Exception:  # noqa: BLE001
                raw = None
                flags.append("bad_tutoring_json")
            if not raw:
                flags.append("empty_tutoring")
            else:
                nodes = [parse_tutoring_item(it, available_figures, missing_figs) for it in raw]
                solution, cyc = order_solution(nodes)
                had_cycle = had_cycle or cyc

        steps.append({
            "step_id": sid,
            "order": order,
            "question": question,
            "problem_type": ptype,
            "answer_type": s.get("answerType"),
            "choices": choices,
            "answer": answer,
            "answer_latex": s.get("answerLatex"),
            "solution": solution,
        })

    if not steps:
        flags.append("no_steps")
    if had_cycle:
        flags.append("unordered_dependencies")   # dangling/cyclic dep refs; original order kept
    if missing_figs:
        flags.append("figure_missing")

    # Figure-dependence: the question/answer/solution references an image, so a
    # text-only rendering may be incomplete. Flag so it can be filtered or routed
    # to a multimodal/OCR path.
    if any(FIGURE_TOKEN.search(t or "") for t in _iter_record_text(p_title, p_body, steps)):
        flags.append("figure_dependent")

    subject, topic, methods, language = derive_taxonomy(p.get("courseName"), p.get("lessonId"))

    # parse "url <label>" oer/license fields
    def split_url_label(v):
        m = re.match(r"\s*(\S+)\s*<(.+?)>\s*$", v or "")
        return (m.group(1), m.group(2)) if m else (v, None)

    oer_url, oer_label = split_url_label(p.get("oer"))
    lic_url, lic_label = split_url_label(p.get("license"))

    record = {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "dataset": "OATutor-Content",
            "repo": "CAHLR/OATutor-Content",
            "problem_id": p.get("id", pid),
            "path": os.path.join("content-pool", pid),
        },
        "provenance": {
            "oer": oer_label, "oer_url": oer_url,
            "license": lic_label, "license_url": lic_url,
        },
        "taxonomy": {
            "course": p.get("courseName"),
            "lesson_id": p.get("lessonId"),
            "lesson": p.get("lesson"),
            "subject": subject,
            "topic": topic,
            "method": methods,
            "skills": sorted(skills),
            "language": language,
        },
        "problem": {
            "title": p_title,
            "body": p_body,
            "figures": sorted({os.path.basename(f) for f in available_figures}),
        },
        "steps": steps,
        "text_format": {"math": "latex_dollar", "image_token": "##name.gif##"},
        "quality_flags": sorted(set(flags)),
    }
    return record, record["quality_flags"], None


# --------------------------------------------------------------------------- #
# training views
# --------------------------------------------------------------------------- #
def linearize_solution(solution, depth=0):
    """Flatten a tutoring tree to a readable worked-solution string."""
    lines = []
    for node in solution:
        prefix = "  " * depth
        tag = "Step" if node["type"] == "hint" else "Ask"
        head = f"{prefix}{tag}: {node['title']}".rstrip(": ").rstrip()
        lines.append(head)
        if node["text"]:
            lines.append(f"{prefix}{node['text']}")
        if node["type"] == "scaffold" and node["scaffold_answer"]:
            lines.append(f"{prefix}Answer: {', '.join(node['scaffold_answer'])}")
        if node["children"]:
            lines.append(linearize_solution(node["children"], depth + 1))
    return "\n".join(l for l in lines if l)


def sft_examples(record):
    """Yield {prompt, completion, meta} per step that has a worked solution."""
    stem = record["problem"]["title"] or record["problem"]["body"]
    figure_dependent = "figure_dependent" in record["quality_flags"]
    for st in record["steps"]:
        if not st["solution"]:
            continue
        worked = linearize_solution(st["solution"])
        if not worked.strip():
            continue
        prompt = (stem + "\n\n" if stem else "") + st["question"]
        if st["choices"]:
            prompt += "\nChoices: " + " | ".join(st["choices"])
        completion = worked + "\n\nFinal answer: " + ", ".join(map(str, st["answer"]))
        yield {
            "prompt": prompt.strip(),
            "completion": completion.strip(),
            "meta": {
                "problem_id": record["source"]["problem_id"],
                "step_id": st["step_id"],
                "subject": record["taxonomy"]["subject"],
                "topic": record["taxonomy"]["topic"],
                "method": record["taxonomy"]["method"],
                "figure_dependent": figure_dependent,
            },
        }


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def run(content_root, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    pool = os.path.join(content_root, "content-pool")
    if not os.path.isdir(pool):
        log.error("content-pool not found under %s", content_root)
        sys.exit(2)

    try:
        commit = subprocess.check_output(
            ["git", "-C", content_root, "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:  # noqa: BLE001
        commit = "unknown"

    skill_model = {}
    sm_path = os.path.join(content_root, "skillModel.json")
    if os.path.exists(sm_path):
        skill_model = load_json(sm_path)

    problem_dirs = sorted(
        d for d in (os.path.join(pool, x) for x in os.listdir(pool))
        if os.path.isdir(d)
    )
    log.info("found %d problem folders", len(problem_dirs))

    records = []
    quarantine = []
    flag_hist = Counter()
    for pd in problem_dirs:
        rec, flags, err = extract_problem(pd, skill_model)
        if err:
            quarantine.append({"path": pd, "error": err})
            continue
        rec["source"]["commit"] = commit
        records.append(rec)
        for f in flags:
            flag_hist[f] += 1

    # ---- dedup by content signature ----
    sig_groups = defaultdict(list)
    for r in records:
        sig = content_signature(r["steps"])
        r["_sig"] = sig
        sig_groups[sig].append(r)

    def primary_rank(r):
        # prefer OpenStax-origin (stable license) then shortest id for determinism
        openstax = 0 if (r["taxonomy"]["course"] or "").startswith("OpenStax") else 1
        return (openstax, r["source"]["problem_id"])

    duplicates_map = {}
    for sig, group in sig_groups.items():
        if len(group) < 2:
            continue
        group_sorted = sorted(group, key=primary_rank)
        primary = group_sorted[0]["source"]["problem_id"]
        for r in group_sorted[1:]:
            r["quality_flags"] = sorted(set(r["quality_flags"] + [f"duplicate_of:{primary}"]))
            duplicates_map[r["source"]["problem_id"]] = primary

    # ---- emit ----
    canonical = os.path.join(out_dir, "oatutor.jsonl")
    systems = os.path.join(out_dir, "oatutor_systems.jsonl")
    sft = os.path.join(out_dir, "sft_steps.jsonl")
    n_sys = n_sft = 0
    with open(canonical, "w", encoding="utf-8") as fc, \
         open(systems, "w", encoding="utf-8") as fs, \
         open(sft, "w", encoding="utf-8") as ft:
        for r in sorted(records, key=lambda x: x["source"]["problem_id"]):
            r.pop("_sig", None)
            line = json.dumps(r, ensure_ascii=False, sort_keys=True)
            fc.write(line + "\n")
            if r["taxonomy"]["topic"] in ("systems_of_equations", "systems_of_inequalities", "nonlinear_systems"):
                fs.write(line + "\n")
                n_sys += 1
            is_dup = any(f.startswith("duplicate_of:") for f in r["quality_flags"])
            if not is_dup:
                for ex in sft_examples(r):
                    ft.write(json.dumps(ex, ensure_ascii=False) + "\n")
                    n_sft += 1

    # ---- per-method + per-step-count splits (training-oriented: duplicates excluded) ----
    by_method_dir = os.path.join(out_dir, "by_method")
    by_steps_dir = os.path.join(out_dir, "by_step_count")
    os.makedirs(by_method_dir, exist_ok=True)
    os.makedirs(by_steps_dir, exist_ok=True)
    method_counts = Counter()
    stepcount_counts = Counter()
    method_files, stepcount_files = {}, {}

    def handle(cache, directory, key):
        if key not in cache:
            cache[key] = open(os.path.join(directory, key + ".jsonl"), "w", encoding="utf-8")
        return cache[key]

    for r in sorted(records, key=lambda x: x["source"]["problem_id"]):
        if any(f.startswith("duplicate_of:") for f in r["quality_flags"]):
            continue
        line = json.dumps(r, ensure_ascii=False, sort_keys=True)
        for m in (r["taxonomy"]["method"] or ["unspecified"]):
            handle(method_files, by_method_dir, m).write(line + "\n")
            method_counts[m] += 1
        # only bucket problems whose method is known (i.e. the systems set) by step count
        if r["taxonomy"]["method"]:
            n = len(r["steps"])
            bucket = f"{n}_step" if n <= 4 else "5plus_step"
            handle(stepcount_files, by_steps_dir, bucket).write(line + "\n")
            stepcount_counts[bucket] += 1
    for fh in list(method_files.values()) + list(stepcount_files.values()):
        fh.close()

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_repo": "CAHLR/OATutor-Content",
        "source_commit": commit,
        "counts": {
            "problem_folders": len(problem_dirs),
            "problems_extracted": len(records),
            "quarantined": len(quarantine),
            "duplicates": len(duplicates_map),
            "unique_after_dedup": len(records) - len(duplicates_map),
            "systems_records": n_sys,
            "sft_step_examples": n_sft,
        },
        "quality_flag_histogram": dict(flag_hist.most_common()),
        "by_method_counts": dict(method_counts.most_common()),
        "by_step_count": dict(sorted(stepcount_counts.items())),
        "outputs": {
            "canonical": "oatutor.jsonl",
            "systems": "oatutor_systems.jsonl",
            "sft": "sft_steps.jsonl",
            "by_method_dir": "by_method/",
            "by_step_count_dir": "by_step_count/",
            "duplicates": "duplicates.json",
            "quarantine": "quarantine.json",
        },
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    with open(os.path.join(out_dir, "duplicates.json"), "w", encoding="utf-8") as fh:
        json.dump(duplicates_map, fh, indent=2)
    with open(os.path.join(out_dir, "quarantine.json"), "w", encoding="utf-8") as fh:
        json.dump(quarantine, fh, indent=2)

    log.info("done. %s", json.dumps(manifest["counts"], indent=2))
    return manifest


def main():
    ap = argparse.ArgumentParser(description="Extract OATutor-Content into a clean JSONL dataset.")
    ap.add_argument("--content-root", required=True, help="Path to a local OATutor-Content clone.")
    ap.add_argument("--out-dir", default="data", help="Output directory.")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )
    run(args.content_root, args.out_dir)


if __name__ == "__main__":
    main()
