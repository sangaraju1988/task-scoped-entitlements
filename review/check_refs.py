"""Reference gate: every \\cite key is defined in refs.bib; report bib entries never cited (they are omitted by
BibTeX, but listed here); every cited entry was resolved by scripts/check_bib.py (review/bib-check-2.txt)."""
import glob, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tex = " ".join(open(p).read() for p in glob.glob(os.path.join(ROOT, "paper", "sections", "*.tex")) + [os.path.join(ROOT, "paper", "main.tex")] if os.path.exists(p))
cited = set()
for m in re.finditer(r"\\cite\{([^}]*)\}", tex):
    cited |= {k.strip() for k in m.group(1).split(",")}
bib = open(os.path.join(ROOT, "paper", "refs.bib")).read()
keys = set(re.findall(r"@\w+\{([^,\s]+),", bib))
check = open(os.path.join(ROOT, "review", "bib-check-2.txt")).read()
resolved = {l.split(" | ")[0] for l in check.splitlines() if " | " in l and (" OK " in l or "CHECK" in l or "URL" in l or "NOID" in l)}
undefined = sorted(cited - keys)
uncited = sorted(keys - cited)
unresolved = sorted(k for k in cited if k not in resolved)
doi = sum(1 for k in cited if re.search(r"@\w+\{" + re.escape(k) + r",[^@]*doi=", bib))
report = [f"cited: {len(cited)}; defined in bib: {len(keys)}; cited with DOI: {doi}",
          f"undefined citations: {undefined}", f"cited but not resolved by check_bib: {unresolved}",
          f"bib entries not cited (dropped by BibTeX): {uncited}"]
open(os.path.join(ROOT, "review", "refs-report.md"), "w").write("# Reference gate\n\n" + "\n\n".join(report) + "\n")
print("\n".join(report))
