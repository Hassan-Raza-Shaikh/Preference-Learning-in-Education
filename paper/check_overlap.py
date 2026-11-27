#!/usr/bin/env python3
"""Originality check: longest word sequences the paper shares with each source text.

    python paper/check_overlap.py <dir with source texts (*.txt)>

Reports, for each source, the longest run of consecutive words (lower-cased,
punctuation stripped) that also appears in paper/main.tex, and every shared run of
>= MIN words. Short shared runs are expected (technical phrases, quoted findings that are
cited); long runs would indicate copied wording.

Limits: compares only against the source texts given (here, the abstracts that could be
downloaded); it is not a plagiarism-detection service and cannot see unread sources.
Failure control: run with --self-test, which plants a 15-word sentence from a source in a
copy of the paper and must report it.
"""
import glob
import os
import re
import sys

MIN = 8
ROOT = os.path.dirname(os.path.abspath(__file__))


def words(text):
    text = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", text)      # drop LaTeX commands
    text = re.sub(r"[{}$%~^_&#\\]", " ", text)
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())


def shared_runs(a, b, n=MIN):
    grams = {}
    for i in range(len(b) - n + 1):
        grams.setdefault(tuple(b[i:i + n]), i)
    runs, i = [], 0
    while i <= len(a) - n:
        if tuple(a[i:i + n]) in grams:
            j = i + n
            while j < len(a) and " ".join(a[i:j + 1]) in " ".join(b):
                j += 1
            runs.append(" ".join(a[i:j]))
            i = j
        else:
            i += 1
    return runs


def main():
    paper = words(open(os.path.join(ROOT, "main.tex"), encoding="utf-8").read())
    srcdir = sys.argv[1]
    if "--self-test" in sys.argv:
        src = sorted(glob.glob(os.path.join(srcdir, "*.txt")))[0]
        planted = words(open(src, encoding="utf-8").read())[:15]
        found = shared_runs(paper + planted, words(open(src, encoding="utf-8").read()), MIN)
        ok = any(len(r.split()) >= 15 for r in found)
        print("self-test:", "PASS (planted copy detected)" if ok else "FAIL (planted copy missed)")
        sys.exit(0 if ok else 1)
    worst = 0
    for f in sorted(glob.glob(os.path.join(srcdir, "*.txt"))):
        runs = shared_runs(paper, words(open(f, encoding="utf-8").read()))
        longest = max((len(r.split()) for r in runs), default=0)
        worst = max(worst, longest)
        print(f"{os.path.basename(f)}: longest shared run = {longest} words")
        for r in runs:
            print("   -", r)
    print(f"LONGEST SHARED RUN OVERALL: {worst} words (threshold for listing: {MIN})")


if __name__ == "__main__":
    main()
