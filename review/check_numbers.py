"""Number-consistency gate (Section 8.3 of the build plan).

Every number in the paper's prose and tables must come from eval/results via a macro in paper/numbers.tex
(mapped in eval/NUMBERS.md), from a generated table (paper/tables/*.tex, written by eval/aggregate.py), or be a
design constant listed in review/number_whitelist.txt with its source. This script strips LaTeX commands, macros,
citations, labels, math indices and environment arguments, then reports every remaining numeral token that is not
whitelisted. Exit code 1 if any unmapped number remains.
"""
import glob, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WL = {}
for line in open(os.path.join(ROOT, "review", "number_whitelist.txt")):
    line = line.strip()
    if line and not line.startswith("#"):
        tok, why = line.split("|", 1)
        WL[tok.strip()] = why.strip()
PAPER = os.path.join(ROOT, "paper")
macros = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", open(os.path.join(PAPER, "numbers.tex")).read()))
files = [os.path.join(PAPER, "main.tex")] + sorted(glob.glob(os.path.join(PAPER, "sections", "*.tex")))
bad = []
for p in files:
    for ln, line in enumerate(open(p), 1):
        s = re.sub(r"(?<!\\)%.*$", "", line)
        if s.lstrip().startswith(("\\begin{tabular", "\\includegraphics", "\\begin{algorithm", "\\begin{table", "\\begin{figure", "\\history", "\\doi")):
            continue
        s = re.sub(r"\\(cite|ref|label|eqref|input|url|includegraphics|begin|end|newcommand|usepackage|documentclass|address|bibliography\w*|section\*?|subsection\*?)\{[^}]*\}", " ", s)
        s = re.sub(r"\\[A-Za-z]+", " ", s)               # macros (incl. generated numbers)
        s = re.sub(r"\$[^$]*\$", " ", s)                  # inline math (indices like k=0, A1)
        s = re.sub(r"\b(?:[A-Z]{1,2}\d+|E\d|H\d|D\d|I\d)\b", " ", s)  # labels like C1, A4, L12, E5, H2, D3
        s = re.sub(r"\[[^\]]*\]", lambda m: m.group(0) if "CI" in m.group(0) else " ", s)
        for m in re.finditer(r"(?<![A-Za-z_])\d[\d.,{}]*", s):
            tok = m.group(0).replace("{,}", ",").rstrip(".,")
            if tok and tok not in WL:
                bad.append(f"{os.path.relpath(p, ROOT)}:{ln}: '{tok}' in: {line.strip()[:110]}")
open(os.path.join(ROOT, "review", "numbers-report.md"), "w").write(
    "# Number-consistency gate\n\n" + (f"{len(bad)} unmapped numbers:\n\n" + "\n".join("- " + b for b in bad) if bad else "All numbers are macros, generated tables, or whitelisted design constants.") + "\n")
print(len(bad), "unmapped"); print("\n".join(bad[:60]))
sys.exit(1 if bad else 0)
