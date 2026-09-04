"""Uploaded credible set -> portal record shape. Mirrors the aggregator's
convert_credible_set (dig-aggregator-methods credible-sets/credibleSets.py)."""

import math

from variant_sifter_pipeline import uploaded_credible_sets as ucs

GUID = "g" * 64


def _row(chrom, pos, ref, alt, set_id, pp, **extra):
    return {"chromosome": chrom, "position": pos, "reference": ref, "alt": alt,
            "credibleSetId": set_id, "posteriorProbability": pp, **extra}


def _build(rows, **kw):
    kw.setdefault("slug", "susie-v1")
    kw.setdefault("name", "SuSiE v1")
    return ucs.build_uploaded_credible_sets(rows, GUID, "myGwas", **kw)


def test_ids_are_namespaced_and_source_names_the_upload():
    variants, sets_ = _build([_row("1", "100", "A", "G", "1", "0.6")])
    assert variants[0]["credibleSetId"] == "susie-v1:1"
    assert variants[0]["source"] == "upload:susie-v1"
    assert sets_[0]["credibleSetId"] == "susie-v1:1"
    assert sets_[0]["source"] == "upload:susie-v1"
    assert sets_[0]["uploadName"] == "SuSiE v1"


def test_record_shape_matches_the_derived_sets():
    variants, sets_ = _build([_row("chr1", "100", "a", "g", "1", "0.6", pValue="1e-8", beta="0.1",
                                   se="0.02", n="1000", rsid="rs1")], ancestry="EUR")
    v = variants[0]
    assert v["phenotype"] == GUID and v["dataset"] == "myGwas" and v["ancestry"] == "EUR"
    assert (v["chromosome"], v["position"], v["reference"], v["alt"]) == ("1", 100, "A", "G")
    assert v["varId"] == "1:100:A:G"
    assert (v["pValue"], v["beta"], v["stdErr"], v["n"], v["dbSNP"]) == (1e-8, 0.1, 0.02, 1000.0, "rs1")
    assert (v["clumpStart"], v["clumpEnd"], v["leadSNP"]) == (100, 101, True)
    s = sets_[0]
    assert (s["phenotype"], s["dataset"], s["chromosome"], s["start"], s["end"], s["ancestry"]) == \
        (GUID, "myGwas", "1", 100, 101, "EUR")


def test_optional_fields_are_absent_when_the_upload_lacks_them():
    variants, _ = _build([_row("1", "100", "A", "G", "1", "0.6")])
    assert not {"pValue", "beta", "stdErr", "n", "dbSNP", "ancestry"} & set(variants[0])


def test_posterior_probabilities_are_renormalised_per_set():
    variants, _ = _build([_row("1", "100", "A", "G", "1", "0.2"), _row("1", "200", "C", "T", "1", "0.2"),
                          _row("2", "300", "A", "C", "2", "3")])
    by_set = {}
    for v in variants:
        by_set.setdefault(v["credibleSetId"], []).append(v["posteriorProbability"])
    assert by_set["susie-v1:1"] == [0.5, 0.5]
    assert by_set["susie-v1:2"] == [1.0]
    assert all(math.isclose(sum(p), 1.0) for p in by_set.values())


def test_lead_snp_is_highest_pp_with_lowest_position_breaking_ties():
    variants, _ = _build([_row("1", "300", "A", "G", "1", "0.4"), _row("1", "100", "C", "T", "1", "0.4"),
                          _row("1", "200", "G", "A", "1", "0.2")])
    leads = [v["position"] for v in variants if v["leadSNP"]]
    assert leads == [100]


def test_clump_bounds_span_the_set():
    variants, sets_ = _build([_row("1", "300", "A", "G", "1", "0.5"), _row("1", "100", "C", "T", "1", "0.5")])
    assert all((v["clumpStart"], v["clumpEnd"]) == (100, 301) for v in variants)
    assert (sets_[0]["start"], sets_[0]["end"]) == (100, 301)


def test_non_positive_pp_rows_and_duplicates_are_dropped():
    variants, _ = _build([_row("1", "100", "A", "G", "1", "0"), _row("1", "200", "C", "T", "1", "0.5"),
                          _row("1", "200", "c", "t", "1", "0.5")])
    assert [v["position"] for v in variants] == [200]


def test_variants_sort_by_set_then_position_and_sets_by_locus():
    variants, sets_ = _build([_row("X", "50", "A", "G", "b", "1"), _row("2", "900", "A", "G", "a", "0.5"),
                              _row("2", "100", "C", "T", "a", "0.5"), _row("1", "5", "A", "G", "c", "1")])
    assert [(v["credibleSetId"], v["position"]) for v in variants] == [
        ("susie-v1:a", 100), ("susie-v1:a", 900), ("susie-v1:b", 50), ("susie-v1:c", 5)]
    assert [(s["chromosome"], s["start"]) for s in sets_] == [("1", 5), ("2", 100), ("X", 50)]


def test_refresh_var_ids_follows_the_alleles():
    rows = [{"chromosome": "1", "position": 100, "reference": "G", "alt": "A", "varId": "1:100:A:G"}]
    ucs.refresh_var_ids(rows)
    assert rows[0]["varId"] == "1:100:G:A"


def test_alignment_is_the_sign_against_the_lead_beta():
    rows = [
        {"credibleSetId": "s:1", "leadSNP": True, "beta": -0.5},
        {"credibleSetId": "s:1", "leadSNP": False, "beta": 0.2},
        {"credibleSetId": "s:1", "leadSNP": False, "beta": -0.1},
        {"credibleSetId": "s:1", "leadSNP": False},                    # no beta -> no alignment
        {"credibleSetId": "s:2", "leadSNP": True},                     # lead without beta
        {"credibleSetId": "s:2", "leadSNP": False, "beta": 0.3},
    ]
    ucs.add_alignment(rows)
    assert [r.get("alignment") for r in rows] == [1.0, -1.0, 1.0, None, None, None]
