import math
import pytest
from falcon_prep.zscore import derive


def test_beta_and_se_gives_z():
    beta, se, z = derive(beta=0.5, se=0.1, pvalue=None, zscore=None)
    assert beta == 0.5
    assert se == 0.1
    assert z == pytest.approx(5.0)


def test_explicit_z_is_preferred_over_beta_over_se():
    beta, se, z = derive(beta=0.5, se=0.1, pvalue=None, zscore=4.2)
    assert z == 4.2


def test_beta_and_pvalue_derives_z_and_se():
    # p = 5.733e-7 is |Z| = 5 two-tailed
    beta, se, z = derive(beta=0.5, se=None, pvalue=5.733e-7, zscore=None)
    assert z == pytest.approx(5.0, abs=1e-3)
    assert se == pytest.approx(0.1, abs=1e-3)


def test_negative_beta_gives_negative_z():
    _, _, z = derive(beta=-0.5, se=None, pvalue=5.733e-7, zscore=None)
    assert z == pytest.approx(-5.0, abs=1e-3)


def test_underflowed_pvalue_is_clamped_not_crashed():
    _, _, z = derive(beta=0.5, se=None, pvalue=0.0, zscore=None)
    assert math.isfinite(z)
    assert z > 30


def test_zero_se_is_rejected():
    assert derive(beta=0.5, se=0.0, pvalue=None, zscore=None) is None


def test_missing_beta_is_rejected():
    assert derive(beta=None, se=0.1, pvalue=1e-8, zscore=None) is None


def test_no_usable_combination_is_rejected():
    assert derive(beta=0.5, se=None, pvalue=None, zscore=None) is None


def test_pvalue_above_one_is_rejected():
    assert derive(beta=0.5, se=None, pvalue=1.5, zscore=None) is None
    assert derive(beta=0.5, se=None, pvalue=2.0, zscore=None) is None


def test_zero_beta_without_explicit_se_is_rejected():
    # SE would derive to 0.0, unusable as a downstream denominator.
    assert derive(beta=0.0, se=None, pvalue=None, zscore=4.2) is None
    assert derive(beta=0.0, se=None, pvalue=5.733e-7, zscore=None) is None


def test_zero_beta_with_explicit_se_is_kept():
    assert derive(beta=0.0, se=0.1, pvalue=None, zscore=None) == (0.0, 0.1, 0.0)


def test_overflowing_inputs_are_rejected():
    assert derive(beta=1e300, se=None, pvalue=None, zscore=1e-300) is None
    assert derive(beta=1.0, se=1e-320, pvalue=None, zscore=None) is None
