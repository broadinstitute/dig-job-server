import math

from variant_sifter_pipeline.associations import build_associations


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


def test_optional_fields_are_emitted_only_when_present():
    """The sifter drives table columns and filters off field PRESENCE, so an
    absent upload column must leave the field out rather than emit a null."""
    rows = [{"chromosome": "1", "position": 10, "reference": "A", "alt": "G",
             "pValue": 1e-9, "beta": 0.2, "se": 0.05,
             "eaf": 0.31, "maf": 0.31, "n": 5000}]
    rec = build_associations(rows, "g", ancestry="EUR")[0]
    assert rec["eaf"] == 0.31 and rec["maf"] == 0.31
    assert rec["n"] == 5000
    assert rec["ancestry"] == "EUR"

    bare = [{"chromosome": "1", "position": 10, "reference": "A", "alt": "G",
             "pValue": 1e-9, "beta": 0.2}]
    rec2 = build_associations(bare, "g")[0]
    for absent in ("eaf", "maf", "n", "ancestry", "stdErr", "zScore"):
        assert absent not in rec2


def test_effective_n_is_the_per_dataset_fallback_for_n():
    rows = [{"chromosome": "1", "position": 10, "reference": "A", "alt": "G",
             "pValue": 1e-9, "beta": 0.2}]
    assert build_associations(rows, "g", effective_n=10995)[0]["n"] == 10995
    # A per-row n wins over the dataset-level fallback.
    rows[0]["n"] = 42
    assert build_associations(rows, "g", effective_n=10995)[0]["n"] == 42


def test_zscore_from_the_file_is_used_when_there_is_no_standard_error():
    """Munged sumstats often carry Z and no SE; without this the column is lost."""
    rows = [{"chromosome": "1", "position": 10, "reference": "A", "alt": "G",
             "pValue": 1e-9, "beta": 0.2, "zScore": 4.0}]
    assert build_associations(rows, "g")[0]["zScore"] == 4.0
    # But a derived z (beta/se) is preferred, since it matches the emitted beta.
    rows[0]["se"] = 0.05
    assert build_associations(rows, "g")[0]["zScore"] == 4.0


def test_zero_pvalues_are_floored_to_the_smallest_representable_p():
    """GWAS Catalog files report p = 0 for underflowed values (605 rows in the
    Vitamin D upload); -log10(0) is Infinity in the portal's LocusZoom plot."""
    rows = [
        {"chromosome": "4", "position": 72618334, "reference": "A", "alt": "C",
         "pValue": "0.0", "beta": 1.0, "se": 0.005},
        {"chromosome": "4", "position": 72618335, "reference": "A", "alt": "C",
         "beta": 1.0, "se": 0.005},                     # derived p underflows too
        {"chromosome": "4", "position": 72618336, "reference": "A", "alt": "C",
         "pValue": 1e-300, "beta": 1.0, "se": 0.1},     # tiny but nonzero: untouched
    ]
    out = build_associations(rows, guid="g", p_threshold=0.05)
    assert [r["pValue"] for r in out] == [1e-323, 1e-323, 1e-300]
    assert all(math.isfinite(-math.log10(r["pValue"])) for r in out)
