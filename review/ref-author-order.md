# Reference author-order check (2026-11-27)

Every bibliography entry with a DOI (Crossref) or arXiv ID was checked: the bib's author list must be a prefix of
the source's author list, in the same order. 79 entries checked. All residual differences are source-side
artifacts, each confirmed:

| Entry | Difference | Resolution |
|---|---|---|
| rfc8693 | Crossref omits Campbell | The RFC text lists M. Jones, A. Nadalin, B. Campbell (Ed.), J. Bradley, C. Mortimore |
| denning1979tracker | Crossref omits Schwartz | The paper lists Denning, Denning, Schwartz (ACM TODS 1979) |
| adam1989security | Crossref spells "Worthmann" | The author is John C. Wortmann |
| miyamoto2026pccsql | Crossref swaps given/family ("Miyamoto Ryoto") | The author is Ryoto Miyamoto |
| li2023bird | Crossref swaps given/family ("Ma Chenhao") | The author is Chenhao Ma |
| debenedetti2024agentdojo, debenedetti2026camel, costa2025fides | Accents (Tramèr, Köpf) | Same names |
| nist80053r5 | Corporate author | n/a |

MiniScope (arXiv 2512.11147): the abstract page lists v1 (2025-12-11) and v2 (2026-10-06). The bib follows v2's
title and author order (Zhu, Huang, Tseng, Vernik, Patil, Fang, Popa) and notes the v1 title.
SessionBound/FactGate (arXiv 2607.00751): v1 is titled SessionBound and v2 FactGate (single author, Minmin Wu); both
titles are in the entry.
