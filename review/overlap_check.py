"""Word 8-gram overlap between this paper's text and the author's prior papers found locally.
Reports the fraction of this paper's 8-grams that occur in each prior document, and every shared passage
(maximal runs of shared 8-grams). Output: review/overlap-report.md"""
import glob, os, re, sys
from pypdf import PdfReader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIOR = sorted(set(
    glob.glob(os.path.expanduser("~/Documents/AgenticAIPapers/*.pdf")) +
    glob.glob(os.path.expanduser("~/Documents/AgenticAIPapers/*/paper/*.tex")) +
    glob.glob(os.path.expanduser("~/Documents/AgenticAIPapers/*/paper/sections/*.tex")) +
    glob.glob(os.path.expanduser("~/Documents/AgenticAIPapers/*/paper/*.pdf")) +
    glob.glob(os.path.expanduser("~/Documents/AgenticAIPapers/tools/tmlr/*.pdf"))))
N = 8


def text_of(p):
    if p.endswith(".pdf"):
        try:
            return " ".join((pg.extract_text() or "") for pg in PdfReader(p).pages)
        except Exception as e:
            return ""
    t = open(p, errors="ignore").read()
    t = re.sub(r"(?m)%.*$", "", t)
    t = re.sub(r"\\(cite|ref|label|eqref)\{[^}]*\}", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    return t


def words(t):
    return re.findall(r"[a-z]+", t.lower())


def grams(w):
    return {tuple(w[i:i + N]) for i in range(len(w) - N + 1)}


def main():
    ours_files = sorted(glob.glob(os.path.join(ROOT, "paper", "sections", "*.tex"))) + [os.path.join(ROOT, "paper", "main.tex")]
    ours_w = words(" ".join(text_of(p) for p in ours_files if os.path.exists(p)))
    ours_g = [tuple(ours_w[i:i + N]) for i in range(len(ours_w) - N + 1)]
    lines = ["# Overlap check (word 8-grams)\n", f"This paper: {len(ours_g)} 8-grams from {len(ours_files)} files.\n",
             "| prior document | shared 8-grams | % of this paper |", "|---|---|---|"]
    passages = []
    for p in PRIOR:
        pg = grams(words(text_of(p)))
        if not pg:
            lines.append(f"| {p.replace(os.path.expanduser('~'), '~')} | (no extractable text) | - |"); continue
        hit = [g in pg for g in ours_g]
        n = sum(hit)
        lines.append(f"| {p.replace(os.path.expanduser('~'), '~')} | {n} | {100*n/max(1,len(ours_g)):.2f} |")
        i = 0
        while i < len(hit):
            if hit[i]:
                j = i
                while j < len(hit) and hit[j]:
                    j += 1
                passages.append((p, " ".join(ours_w[i:j + N - 1])))
                i = j
            else:
                i += 1
    lines.append("\n## Shared passages (each is a maximal run of shared 8-grams)\n")
    for p, s in passages:
        lines.append(f"- [{os.path.basename(p)}] {s}")
    open(os.path.join(ROOT, "review", "overlap-report.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[:4 + len(PRIOR)]))
    print("shared passages:", len(passages))


if __name__ == "__main__":
    main()
