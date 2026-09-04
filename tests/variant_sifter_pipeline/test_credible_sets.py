"""Credible-set derivation: the port of the portal's bottom-line recipe
(PLINK LD-clumping + Wakefield-style ABF posterior probabilities).

The reference implementations live in dig-aggregator-methods
(bottom-line/runPlink.py and credible-sets/credibleSets.py); these tests pin
the behaviors that must survive the port, not the reference code's shape.
"""

import json
import math
from unittest.mock import MagicMock, patch

from variant_sifter_pipeline import credible_sets as cs


# --- bayes_pp: ABF posterior probabilities within one clump ---------------


def test_single_variant_clump_gets_pp_one():
    assert cs.bayes_pp([5e-9]) == [1.0]


def test_equal_pvalues_split_pp_equally():
    pps = cs.bayes_pp([1e-8, 1e-8])
    assert pps == [0.5, 0.5]


def test_lower_pvalue_gets_higher_pp():
    pps = cs.bayes_pp([1e-12, 1e-6])
    assert pps[0] > pps[1]


def test_pp_sums_to_one():
    pps = cs.bayes_pp([1e-10, 3e-9, 5e-8, 2e-6])
    assert math.isclose(sum(pps), 1.0)
    assert all(0.0 < p < 1.0 for p in pps)


def test_extreme_pvalues_stay_finite():
    """The aggregator clamps p below 1e-323 (norm.ppf hits infinity there);
    p=0.0 appears in real uploads and must not produce inf/nan."""
    pps = cs.bayes_pp([0.0, 1e-320, 1e-8])
    assert all(math.isfinite(p) for p in pps)
    assert math.isclose(sum(pps), 1.0)


def test_gws_pvalue_dominates_a_marginal_one():
    """k=0.974 was chosen so p=5e-8 lands around PP 0.75 against the implicit
    prior; the practical property we rely on is that a genome-wide-significant
    variant crushes a merely-nominal one in the same clump."""
    pps = cs.bayes_pp([5e-8, 1e-3])
    assert pps[0] > 0.99


# --- clump_groups: parse plink's .clumped report into rsID groups ---------

# Real plink 1.9 --clump output shape: whitespace-aligned columns, SP2 is a
# comma list of rsID(allele-file-number) or the literal NONE, and the report
# ends with blank lines.
_CLUMPED = """\
 CHR    F              SNP         BP        P    TOTAL   NSIG    S05    S01   S001  S0001    SP2
   9    1        rs1333049   22125503 2.28e-20       2      0      0      0      1      1 rs4977574(1),rs2891168(1)
   9    1        rs7859727   22124477 1.00e-09       0      0      0      0      0      0 NONE

"""


def test_clump_groups_include_index_snp_and_sp2_members():
    groups = cs.clump_groups(_CLUMPED)
    assert {"rs1333049", "rs4977574", "rs2891168"} in groups


def test_sp2_none_is_a_singleton_group():
    groups = cs.clump_groups(_CLUMPED)
    assert {"rs7859727"} in groups
    assert len(groups) == 2


def test_groups_sharing_a_member_are_merged():
    """runPlink.py merges clumps via connected components; the port must keep
    that: a SNP claimed by two index SNPs joins their clumps into one set."""
    text = (
        " CHR F SNP BP P TOTAL NSIG S05 S01 S001 S0001 SP2\n"
        "   1 1 rs1 100 1e-10 1 0 0 0 0 1 rs2(1)\n"
        "   1 1 rs3 900 1e-9 1 0 0 0 0 1 rs2(1)\n"
    )
    groups = cs.clump_groups(text)
    assert groups == [{"rs1", "rs2", "rs3"}]


# --- derive_credible_sets: records in, variant + locus rows out -----------


def _rec(pos, p, rsid=None, beta=None, chrom="9"):
    r = {"phenotype": "guidX", "chromosome": chrom, "position": pos,
         "reference": "T", "alt": "C", "pValue": p}
    if rsid is not None:
        r["dbSNP"] = rsid
    if beta is not None:
        r["beta"] = beta
        r["stdErr"] = 0.01
    return r


class _plink_stub:
    """A run_plink stand-in that records what it was asked to clump."""

    def __init__(self, clumped_text):
        self.clumped_text = clumped_text
        self.calls = []

    def __call__(self, assoc_rows):
        self.calls.append(list(assoc_rows))
        return self.clumped_text


def test_derive_produces_variant_and_locus_rows():
    records = [
        _rec(100, 1e-12, rsid="rs1", beta=0.1),
        _rec(200, 1e-7, rsid="rs2", beta=-0.05),
        _rec(300, 1e-3, rsid="rs3"),               # above p2, never a candidate
    ]
    clumped = (
        " CHR F SNP BP P TOTAL NSIG S05 S01 S001 S0001 SP2\n"
        "   9 1 rs1 100 1e-12 1 0 0 0 0 1 rs2(1)\n"
    )
    variants, sets_ = cs.derive_credible_sets(
        records, "guidX", dataset="myGwas", ancestry="EU",
        run_plink=_plink_stub(clumped))

    assert [v["varId"] for v in variants] == ["9:100:T:C", "9:200:T:C"]
    v1, v2 = variants
    assert v1["credibleSetId"] == v2["credibleSetId"] == "1_sifter"
    assert math.isclose(v1["posteriorProbability"] + v2["posteriorProbability"], 1.0)
    assert v1["posteriorProbability"] > v2["posteriorProbability"]
    assert (v1["clumpStart"], v1["clumpEnd"]) == (100, 201)
    assert v1["phenotype"] == "guidX" and v1["dataset"] == "myGwas"
    assert v1["ancestry"] == "EU"
    assert v1["beta"] == 0.1 and v1["stdErr"] == 0.01
    assert v1["dbSNP"] == "rs1"

    assert sets_ == [{
        "phenotype": "guidX", "credibleSetId": "1_sifter", "dataset": "myGwas",
        "ancestry": "EU", "chromosome": "9", "start": 100, "end": 201,
    }]


def test_lead_snp_is_lowest_pvalue_and_alignment_signs_follow_its_beta():
    records = [_rec(100, 1e-12, rsid="rs1", beta=0.1),
               _rec(200, 1e-7, rsid="rs2", beta=-0.05)]
    clumped = (
        " CHR F SNP BP P TOTAL NSIG S05 S01 S001 S0001 SP2\n"
        "   9 1 rs1 100 1e-12 1 0 0 0 0 1 rs2(1)\n"
    )
    variants, _ = cs.derive_credible_sets(
        records, "guidX", dataset="d", run_plink=_plink_stub(clumped))
    by_rsid = {v["dbSNP"]: v for v in variants}
    assert by_rsid["rs1"]["leadSNP"] is True
    assert by_rsid["rs2"]["leadSNP"] is False
    assert by_rsid["rs1"]["alignment"] == 1.0
    assert by_rsid["rs2"]["alignment"] == -1.0


def test_gws_variant_without_rsid_becomes_a_singleton_set():
    """clumpedAssociations keeps rsID-less genome-wide-significant variants as
    their own 1bp 'rare' clumps rather than silently dropping a top hit."""
    records = [_rec(500, 1e-9)]
    variants, sets_ = cs.derive_credible_sets(
        records, "guidX", dataset="d", run_plink=_plink_stub(None))
    assert len(variants) == 1 and len(sets_) == 1
    v = variants[0]
    assert v["posteriorProbability"] == 1.0
    assert v["leadSNP"] is True
    assert (v["clumpStart"], v["clumpEnd"]) == (500, 501)


def test_sub_gws_variant_without_rsid_is_dropped():
    """Between p2 and p1 an rsID-less variant can't be LD-clumped and isn't
    significant enough for a singleton set; production drops it too."""
    records = [_rec(100, 1e-12, rsid="rs1"), _rec(200, 1e-6)]
    clumped = (
        " CHR F SNP BP P TOTAL NSIG S05 S01 S001 S0001 SP2\n"
        "   9 1 rs1 100 1e-12 0 0 0 0 0 0 NONE\n"
    )
    variants, _ = cs.derive_credible_sets(
        records, "guidX", dataset="d", run_plink=_plink_stub(clumped))
    assert [v["varId"] for v in variants] == ["9:100:T:C"]


def test_no_gws_signal_yields_empty_outputs_and_skips_plink():
    """No variant at p<=5e-8 means no set can seed; plink must not even run."""
    run_plink = _plink_stub(None)
    variants, sets_ = cs.derive_credible_sets(
        [_rec(100, 1e-7, rsid="rs1")], "guidX", dataset="d", run_plink=run_plink)
    assert (variants, sets_) == ([], [])
    assert run_plink.calls == []


def test_candidates_not_in_any_clump_are_excluded():
    """plink omits assoc-file SNPs absent from the LD panel or outside every
    clump; they must not leak into a credible set."""
    records = [_rec(100, 1e-12, rsid="rs1"), _rec(200, 1e-7, rsid="rs_unknown")]
    clumped = (
        " CHR F SNP BP P TOTAL NSIG S05 S01 S001 S0001 SP2\n"
        "   9 1 rs1 100 1e-12 0 0 0 0 0 0 NONE\n"
    )
    variants, _ = cs.derive_credible_sets(
        records, "guidX", dataset="d", run_plink=_plink_stub(clumped))
    assert [v["dbSNP"] for v in variants] == ["rs1"]


def test_rsid_lookup_fills_missing_rsids_before_clumping():
    records = [_rec(100, 1e-12), _rec(200, 1e-7, rsid="rs2")]
    clumped = (
        " CHR F SNP BP P TOTAL NSIG S05 S01 S001 S0001 SP2\n"
        "   9 1 rs1 100 1e-12 1 0 0 0 0 1 rs2(1)\n"
    )
    run_plink = _plink_stub(clumped)
    variants, _ = cs.derive_credible_sets(
        records, "guidX", dataset="d", run_plink=run_plink,
        rsid_lookup=lambda varids: {"9:100:T:C": "rs1"})
    assert {v["varId"] for v in variants} == {"9:100:T:C", "9:200:T:C"}
    assert {r["dbSNP"] for r in run_plink.calls[0]} == {"rs1", "rs2"}


def test_two_signals_get_distinct_sets_ordered_by_position():
    records = [_rec(5000, 1e-10, rsid="rs10", chrom="2"),
               _rec(100, 1e-12, rsid="rs1", chrom="2")]
    clumped = (
        " CHR F SNP BP P TOTAL NSIG S05 S01 S001 S0001 SP2\n"
        "   2 1 rs10 5000 1e-10 0 0 0 0 0 0 NONE\n"
        "   2 1 rs1 100 1e-12 0 0 0 0 0 0 NONE\n"
    )
    variants, sets_ = cs.derive_credible_sets(
        records, "guidX", dataset="d", run_plink=_plink_stub(clumped))
    assert [s["credibleSetId"] for s in sets_] == ["1_sifter", "2_sifter"]
    assert [s["start"] for s in sets_] == [100, 5000]
    # variant rows arrive grouped by set, in the same order
    assert [v["credibleSetId"] for v in variants] == ["1_sifter", "2_sifter"]


# --- g1000_panel: ancestry code -> 1000G LD panel --------------------------


def test_panel_accepts_both_portal_and_1000g_ancestry_codes():
    """Upload metadata stores 1000G-style codes (EUR/AMR/...; seen on real
    datasets), while the aggregator map speaks portal codes (EU/HS/...). Both
    must resolve; AMR->eur by fallthrough would clump against the wrong LD."""
    assert cs.g1000_panel("EU") == "eur"
    assert cs.g1000_panel("EUR") == "eur"
    assert cs.g1000_panel("AMR") == "amr"
    assert cs.g1000_panel("AFR") == "afr"
    assert cs.g1000_panel("EAS") == "eas"
    assert cs.g1000_panel("SAS") == "sas"


def test_panel_defaults_to_eur_for_missing_or_unknown_ancestry():
    """Mixed/absent uses EU like the portal's trans-ethnic bottom line."""
    assert cs.g1000_panel(None) == "eur"
    assert cs.g1000_panel("Mixed") == "eur"
    assert cs.g1000_panel("martian") == "eur"


# --- write_derived_credible_sets: write both objects; indexing is run.py's job


def test_write_derived_writes_both_objects_where_the_indexers_look():
    records = [_rec(500, 1e-9)]     # singleton set via the rsID-less path
    s3 = MagicMock()
    with patch.object(cs, "make_plink_runner", return_value=_plink_stub(None)), \
         patch.object(cs, "dbsnp_rsid_lookup", return_value={}):
        n = cs.write_derived_credible_sets(
            s3, "bkt", records, "guidX", dataset="d", ancestry="EU")

    assert n == 1
    writes = {kw["Key"]: kw["Body"] for _, kw in s3.put_object.call_args_list}
    assert set(writes) == {"credible-variants/guidX/variants.json",
                           "credible-sets/guidX/sets.json"}
    variant = json.loads(writes["credible-variants/guidX/variants.json"].decode().strip())
    assert variant["posteriorProbability"] == 1.0
    set_rec = json.loads(writes["credible-sets/guidX/sets.json"].decode().strip())
    assert (set_rec["start"], set_rec["end"]) == (500, 501)


def test_write_derived_still_writes_empty_objects_without_a_signal():
    """No genome-wide-significant hit: write empty objects anyway, so the
    indexes run.py builds return cleanly instead of 404ing."""
    s3 = MagicMock()
    with patch.object(cs, "make_plink_runner", return_value=_plink_stub(None)), \
         patch.object(cs, "dbsnp_rsid_lookup", return_value={}):
        n = cs.write_derived_credible_sets(s3, "bkt", [_rec(100, 1e-4)], "guidX", dataset="d")

    assert n == 0
    bodies = [kw["Body"] for _, kw in s3.put_object.call_args_list]
    assert len(bodies) == 2 and all(b == b"" for b in bodies)
