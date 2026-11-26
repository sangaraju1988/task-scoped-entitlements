import numpy as np
from eval.stats import boot_ci, mcnemar_exact, wilcoxon_paired, holm, geomean

def test_boot_ci_contains_mean():
    m, lo, hi = boot_ci([0, 1] * 50)
    assert lo < m < hi and abs(m - 0.5) < 1e-9

def test_mcnemar():
    a = [1]*10 + [0]*10; b = [1]*10 + [1]*10
    n01, n10, p = mcnemar_exact(a, b)
    assert (n01, n10) == (10, 0) and p < 0.01

def test_wilcoxon_effect_sign():
    p, r, n = wilcoxon_paired([5, 6, 7, 8, 9, 10], [1, 1, 1, 1, 1, 1])
    assert r == 1.0 and p < 0.05

def test_holm():
    assert holm([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]

def test_geomean():
    assert abs(geomean([1, 100]) - 10) < 1e-9
