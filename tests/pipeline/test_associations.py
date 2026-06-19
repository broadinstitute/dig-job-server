import math

from pipeline.variant_sifter.associations import build_associations


def test_filters_by_pvalue_keys_by_guid_and_sorts_by_locus():
    rows = [
        {"chromosome": "8", "position": 200, "reference": "C", "alt": "T",
         "pValue": 1e-12, "beta": -0.3, "se": 0.04, "rsid": "rs2"},
        {"chromosome": "8", "position": 100, "reference": "A", "alt": "G",
         "pValue": 0.4, "beta": 0.01, "se": 0.02, "rsid": "rs1"},   # dropped
        {"chromosome": "8", "position": 150, "reference": "G", "alt": "A",
         "pValue": 0.01, "beta": 0.2, "se": 0.05, "rsid": "rs3"},
    ]
    out = build_associations(rows, guid="guidAAA", p_threshold=0.05)
    assert [r["position"] for r in out] == [150, 200]      # filtered + locus-sorted
    assert all(r["phenotype"] == "guidAAA" for r in out)
    assert out[1]["dbSNP"] == "rs2"        # rsid -> dbSNP
    assert out[1]["stdErr"] == 0.04        # se -> stdErr
    assert "consequence" not in out[0]     # VEP deferred
    assert "maf" not in out[0]


def test_derives_pvalue_from_beta_se_when_absent():
    rows = [{"chromosome": "1", "position": 5, "reference": "A", "alt": "C",
             "beta": 6.0, "se": 1.0}]   # z=6 -> p ~ 2e-9
    out = build_associations(rows, "g", p_threshold=0.05)
    assert len(out) == 1
    assert out[0]["zScore"] == 6.0
    assert out[0]["pValue"] < 1e-6


def test_beta_from_odds_ratio_for_binary_traits():
    rows = [{"chromosome": "2", "position": 9, "reference": "G", "alt": "T",
             "oddsRatio": math.e ** 0.5, "se": 0.05}]   # beta = 0.5
    out = build_associations(rows, "g", p_threshold=0.05)
    assert len(out) == 1
    assert abs(out[0]["beta"] - 0.5) < 1e-9


def test_threshold_inclusive_and_configurable():
    rows = [{"chromosome": "1", "position": 1, "reference": "A", "alt": "C",
             "pValue": 1e-6, "beta": 0.1, "se": 0.02}]
    assert len(build_associations(rows, "g", p_threshold=1e-5)) == 1
    assert len(build_associations(rows, "g", p_threshold=1e-7)) == 0
