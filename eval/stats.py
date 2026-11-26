"""Statistics used in the paper (preregistered): percentile bootstrap CIs, exact McNemar, Wilcoxon signed-rank
with matched-pairs rank-biserial effect size, Holm correction."""
import numpy as np
from scipy import stats as st

B = 10000


def boot_ci(x, fn=np.mean, b=B, seed=0, alpha=0.05):
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return (float("nan"),) * 3
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(b, len(x)))
    vals = np.apply_along_axis(fn, 1, x[idx]) if fn is not np.mean else x[idx].mean(axis=1)
    return float(fn(x)), float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2))


def boot_paired_diff(a, b_, b=B, seed=0):
    """CI of mean(a - b) over paired observations."""
    d = np.asarray(a, dtype=float) - np.asarray(b_, dtype=float)
    return boot_ci(d, b=b, seed=seed)


def geomean(x):
    x = np.asarray(x, dtype=float)
    return float(np.exp(np.mean(np.log(np.maximum(x, 1e-12)))))


def mcnemar_exact(a, b_):
    """a, b_: paired binary outcomes. Returns (n01, n10, two-sided exact p)."""
    a = np.asarray(a, dtype=bool); b_ = np.asarray(b_, dtype=bool)
    n01 = int(np.sum(~a & b_)); n10 = int(np.sum(a & ~b_))
    n = n01 + n10
    p = 1.0 if n == 0 else float(min(1.0, 2 * st.binom.cdf(min(n01, n10), n, 0.5)))
    return n01, n10, p


def wilcoxon_paired(a, b_):
    """Two-sided Wilcoxon signed-rank on paired values; effect size = matched-pairs rank-biserial r."""
    a = np.asarray(a, dtype=float); b_ = np.asarray(b_, dtype=float)
    d = a - b_
    d = d[d != 0]
    if len(d) == 0:
        return 1.0, 0.0, 0
    res = st.wilcoxon(d, zero_method="wilcox", alternative="two-sided")
    ranks = st.rankdata(np.abs(d))
    rpos, rneg = ranks[d > 0].sum(), ranks[d < 0].sum()
    r = float((rpos - rneg) / (rpos + rneg))
    return float(res.pvalue), r, int(len(d))


def holm(pvals):
    """Holm-Bonferroni adjusted p-values (same order as input)."""
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p)
    adj = np.empty(m)
    run = 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (m - i) * p[k]))
        adj[k] = run
    return adj.tolist()
