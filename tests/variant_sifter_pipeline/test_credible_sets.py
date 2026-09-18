"""Credible-set derivation: the port of the aggregator's `finemapping` package
(Open Targets Genetics method: GCTA-COJO index variants, conditional analysis,
Wakefield ABF 95%/99% credible sets).

The reference implementation lives in dig-aggregator-methods (branch
`finemap`, deployed to s3://dig-analysis-bin/cojo/finemapping/); these tests
pin the behaviors that must survive the port. The ABF numbers below were
produced by running the reference `credible_set.calc_credible_sets` on the
same inputs.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from variant_sifter_pipeline import credible_sets as cs


# --- fixtures ---------------------------------------------------------------


def _rec(pos, p, rsid=None, beta=0.1, se=0.01, eaf=0.3, n=20000.0, chrom="9",
         ref="T", alt="C"):
    r = {"phenotype": "guidX", "chromosome": chrom, "position": pos,
         "reference": ref, "alt": alt, "pValue": p}
    if rsid is not None:
        r["dbSNP"] = rsid
    if beta is not None:
        r["beta"] = beta
        r["stdErr"] = se
    if eaf is not None:
        r["eaf"] = eaf
    if n is not None:
        r["n"] = n
    return r


_JMA_HEADER = "Chr\tSNP\tbp\trefA\tfreq\tb\tse\tp\tn\tfreq_geno\tbJ\tbJ_se\tpJ\tLD_r"
_CMA_HEADER = "Chr\tSNP\tbp\trefA\tfreq\tb\tse\tp\tn\tfreq_geno\tbC\tbC_se\tpC"


def _jma(rows):
    """A `.jma.cojo` report naming these rows as the selected SNPs."""
    lines = [_JMA_HEADER]
    for r in rows:
        lines.append("\t".join(map(str, [
            r["chromosome"], r["dbSNP"], r["position"], r["alt"], r["eaf"], r["beta"],
            r["stdErr"], r["pValue"], r["n"], r["eaf"], r["beta"], r["stdErr"],
            r["pValue"], 0])))
    return "\n".join(lines) + "\n"


def _cma(rows, cond=None):
    """A `.cma.cojo` report for these rows; `cond` maps rsID -> (bC, bC_se, pC),
    defaulting to the marginal statistics."""
    cond = cond or {}
    lines = [_CMA_HEADER]
    for r in rows:
        bc, sec, pc = cond.get(r["dbSNP"], (r["beta"], r["stdErr"], r["pValue"]))
        lines.append("\t".join(map(str, [
            r["chromosome"], r["dbSNP"], r["position"], r["alt"], r["eaf"], r["beta"],
            r["stdErr"], r["pValue"], r["n"], r["eaf"], bc, sec, pc])))
    return "\n".join(lines) + "\n"


class _gcta_stub:
    """A GCTA stand-in recording what it was asked to run.

    `jma` is the `.jma.cojo` text (or None); `cond_stats` maps rsID ->
    (bC, bC_se, pC) overrides for the `.cma.cojo` reports, which otherwise
    echo the marginal statistics of every window row."""

    _UNSET = object()

    def __init__(self, jma=None, cond_stats=None, cma=_UNSET):
        self.jma = jma
        self.cond_stats = cond_stats
        self.cma = cma            # explicit `.cma.cojo` override (text or None)
        self.slct_calls = []
        self.cond_calls = []
        self.panel_events = []

    def ensure_panel(self, chrom):
        self.panel_events.append(("ensure", chrom))

    def release_panel(self, chrom):
        self.panel_events.append(("release", chrom))

    def slct(self, chrom, gws_rows):
        self.slct_calls.append((chrom, [r["dbSNP"] for r in gws_rows]))
        return self.jma

    def cond(self, chrom, window_rows, cond_rsids):
        self.cond_calls.append((chrom, [r["dbSNP"] for r in window_rows], list(cond_rsids)))
        if self.cma is not self._UNSET:
            return self.cma
        # Like GCTA, the conditioned-on SNPs themselves are absent from the report.
        return _cma([r for r in window_rows if r["dbSNP"] not in set(cond_rsids)], self.cond_stats)


# --- prepare_sumstats: what the method can work with -------------------------


def test_prepare_keeps_only_rows_with_every_required_field():
    rows = cs.prepare_sumstats([
        _rec(100, 1e-9, rsid="rs1"),
        _rec(200, 1e-9),                          # no rsID
        _rec(300, 1e-9, rsid="rs3", beta=None),   # no beta/stdErr
        _rec(400, 1e-9, rsid="rs4", eaf=None),    # no eaf
        _rec(500, 1e-9, rsid="rs5", n=None),      # no n
    ])
    assert [r["dbSNP"] for r in rows] == ["rs1"]


def test_prepare_applies_the_maf_filter_on_either_allele():
    rows = cs.prepare_sumstats([
        _rec(100, 1e-9, rsid="rs1", eaf=0.005),
        _rec(200, 1e-9, rsid="rs2", eaf=0.995),
        _rec(300, 1e-9, rsid="rs3", eaf=0.01),
        _rec(400, 1e-9, rsid="rs4", eaf=0.99),
    ])
    assert [r["dbSNP"] for r in rows] == ["rs3", "rs4"]


def test_prepare_drops_the_mhc_for_the_dataset_build():
    inside_b37 = _rec(30_000_000, 1e-9, rsid="rs1", chrom="6")
    inside_b38_only = _rec(33_460_000, 1e-9, rsid="rs2", chrom="6")
    elsewhere = _rec(30_000_000, 1e-9, rsid="rs3", chrom="7")
    b37 = cs.prepare_sumstats([inside_b37, inside_b38_only, elsewhere])
    assert [r["dbSNP"] for r in b37] == ["rs2", "rs3"]
    b38 = cs.prepare_sumstats([inside_b37, inside_b38_only, elsewhere], genome_build="GRCh38")
    assert [r["dbSNP"] for r in b38] == ["rs3"]


def test_prepare_coerces_numeric_strings_and_copies_rows():
    src = _rec("100", "1e-9", rsid="rs1", beta="0.1", se="0.01", eaf="0.3", n="20000")
    row = cs.prepare_sumstats([src])[0]
    assert (row["position"], row["pValue"], row["beta"], row["n"]) == (100, 1e-9, 0.1, 20000.0)
    assert src["position"] == "100"


# --- GCTA file formats -------------------------------------------------------


def test_ma_lines_have_the_cojo_columns_with_alt_as_effect_allele():
    lines = cs.ma_lines(cs.prepare_sumstats([_rec(100, 1e-9, rsid="rs1", ref="T", alt="C")]))
    assert lines[0] == "SNP\tA1\tA2\tfreq\tb\tse\tp\tN"
    assert lines[1].split("\t") == ["rs1", "C", "T", "0.3", "0.1", "0.01", "1e-09", "20000.0"]


def test_ma_lines_never_write_a_zero_pvalue():
    lines = cs.ma_lines(cs.prepare_sumstats([_rec(100, 0.0, rsid="rs1")]))
    assert lines[1].split("\t")[6] == repr(cs.MIN_P)


def test_parse_cojo_table_reads_real_headers_and_floats():
    rows = cs.parse_cojo_table(_cma([_rec(100, 1e-9, rsid="rs1")], {"rs1": (0.05, 0.02, 1e-3)}))
    assert rows[0]["SNP"] == "rs1"
    assert (rows[0]["bC"], rows[0]["bC_se"], rows[0]["pC"]) == (0.05, 0.02, 1e-3)
    assert cs.parse_cojo_table(None) == []
    assert cs.parse_cojo_table(_JMA_HEADER + "\n") == []


# --- select_index_variants: the 0 / 1 / many rule ---------------------------


def test_no_gws_variant_means_no_index_and_no_gcta():
    rows = cs.prepare_sumstats([_rec(100, 1e-4, rsid="rs1")])
    slct = MagicMock()
    assert cs.select_index_variants(rows, slct) == []
    slct.assert_not_called()


def test_a_single_gws_variant_is_the_index_without_gcta():
    rows = cs.prepare_sumstats([_rec(100, 1e-9, rsid="rs1"), _rec(200, 1e-4, rsid="rs2")])
    slct = MagicMock()
    assert [r["dbSNP"] for r in cs.select_index_variants(rows, slct)] == ["rs1"]
    slct.assert_not_called()


def test_many_gws_variants_are_clumped_by_gcta_on_the_gws_rows_only():
    rows = cs.prepare_sumstats([
        _rec(100, 1e-9, rsid="rs1"), _rec(200, 1e-10, rsid="rs2"), _rec(300, 1e-4, rsid="rs3")])
    slct = MagicMock(return_value=_jma([rows[1]]))
    assert [r["dbSNP"] for r in cs.select_index_variants(rows, slct)] == ["rs2"]
    assert [r["dbSNP"] for r in slct.call_args.args[0]] == ["rs1", "rs2"]


def test_gcta_producing_no_report_means_no_index():
    rows = cs.prepare_sumstats([_rec(100, 1e-9, rsid="rs1"), _rec(200, 1e-10, rsid="rs2")])
    assert cs.select_index_variants(rows, lambda gws: None) == []


# --- windows and conditioning -------------------------------------------------


def test_window_is_inclusive_kb_either_side():
    rows = cs.prepare_sumstats([_rec(p, 0.01, rsid=f"rs{p}") for p in (0, 500_000, 1_500_000, 1_500_001)])
    assert [r["position"] for r in cs.window(rows, 1_000_000, 500)] == [500_000, 1_500_000]


def test_condition_list_is_the_other_index_variants_inside_the_window():
    rows = cs.prepare_sumstats([_rec(p, 0.01, rsid=f"rs{i}") for i, p in enumerate((100, 200, 300))])
    assert cs.condition_list("rs1", rows, ["rs0", "rs1", "rs2", "rs9"]) == ["rs0", "rs2"]
    assert cs.condition_list("rs1", rows, ["rs1"]) == []


def test_conditional_stats_inner_join_cma_onto_the_window():
    rows = cs.prepare_sumstats([_rec(100, 1e-9, rsid="rs1"), _rec(200, 1e-3, rsid="rs2")])
    cma = _cma(rows[:1], {"rs1": (0.05, 0.02, 1e-3)})   # rs2 filtered by GCTA
    out = cs.conditional_stats(rows, cma)
    assert [r["dbSNP"] for r in out] == ["rs1"]
    assert (out[0]["beta_cond"], out[0]["se_cond"], out[0]["p_cond"]) == (0.05, 0.02, 1e-3)
    assert cs.conditional_stats(rows, None) == []


def test_marginal_as_conditional_copies_the_marginal_statistics():
    rows = cs.prepare_sumstats([_rec(100, 1e-9, rsid="rs1", beta=0.2, se=0.03)])
    out = cs.marginal_as_conditional(rows)[0]
    assert (out["beta_cond"], out["se_cond"], out["p_cond"]) == (0.2, 0.03, 1e-9)


# --- credible_set: Wakefield ABF pinned to the reference implementation -----


def _cond_rows(pvals, eaf=0.3, n=20000.0):
    return [dict(position=i * 100, dbSNP=f"rs{i + 1}", p_cond=p, eaf=eaf, n=n)
            for i, p in enumerate(pvals)]


def test_credible_set_matches_reference_numbers_and_flags():
    """Reference calc_credible_sets on pval_cond=[1e-9,2e-9,1e-8,5e-8,1e-6],
    eaf 0.3, n 20000: rs5 (postprob 0.00078) is outside both sets and below
    the pp threshold; rs4 is in the 99% set only."""
    kept = cs.credible_set(_cond_rows([1e-9, 2e-9, 1e-8, 5e-8, 1e-6]))
    assert [r["dbSNP"] for r in kept] == ["rs1", "rs2", "rs3", "rs4"]
    assert [r["logABF"] for r in kept] == pytest.approx(
        [15.940711086834, 15.268664855954, 13.710690293588, 12.156678641723], rel=1e-9)
    assert [r["postprob"] for r in kept] == pytest.approx(
        [0.608940429681, 0.310963087502, 0.065477046955, 0.013841730814], rel=1e-9)
    assert [r["postprob_cumsum"] for r in kept] == pytest.approx(
        [0.608940429681, 0.919903517183, 0.985380564139, 0.999222294953], rel=1e-9)
    assert [r["is95"] for r in kept] == [True, True, True, False]
    assert [r["is99"] for r in kept] == [True, True, True, True]


def test_credible_set_stops_the_99_set_where_the_reference_does():
    """Reference on pval_cond=[1e-10,3e-10,1e-8,1e-3], eaf 0.4, n 10000: the
    cumulative posterior passes 0.99 at rs2, so rs3 (postprob 0.0086) is out."""
    kept = cs.credible_set(_cond_rows([1e-10, 3e-10, 1e-8, 1e-3], eaf=0.4, n=10000.0))
    assert [r["dbSNP"] for r in kept] == ["rs1", "rs2"]
    assert [r["postprob"] for r in kept] == pytest.approx([0.736967818132, 0.254415891285], rel=1e-9)
    assert [r["postprob_cumsum"] for r in kept] == pytest.approx([0.736967818132, 0.991383709416], rel=1e-9)


def test_credible_set_floors_a_zero_conditional_pvalue_like_the_reference():
    """Reference: pval_cond 0 is replaced by sys.float_info.min, giving
    logABF 372.529643677947 and the whole posterior."""
    rows = [dict(position=1, dbSNP="rsA", p_cond=1e-12, eaf=0.30, n=50000.0),
            dict(position=2, dbSNP="rsB", p_cond=1e-9, eaf=0.05, n=50000.0),
            dict(position=3, dbSNP="rsC", p_cond=1e-4, eaf=0.62, n=40000.0),
            dict(position=4, dbSNP="rsD", p_cond=0.0, eaf=0.9995, n=50000.0)]
    kept = cs.credible_set(rows)
    assert [r["dbSNP"] for r in kept] == ["rsD"]
    assert kept[0]["logABF"] == pytest.approx(372.529643677947, rel=1e-9)
    assert kept[0]["postprob"] == 1.0 and kept[0]["is95"] and kept[0]["is99"]


def test_credible_set_pp_threshold_drops_weak_members_of_the_set():
    rows = _cond_rows([1e-9, 2e-9, 1e-8, 5e-8, 1e-6])
    assert len(cs.credible_set(rows, pp_threshold=0.5)) == 1
    assert len(cs.credible_set(rows, pp_threshold=0.0)) == 4


def test_credible_set_returns_rows_in_position_order_and_empty_for_empty():
    rows = list(reversed(_cond_rows([2e-9, 1e-9])))
    assert [r["position"] for r in cs.credible_set(rows)] == [0, 100]
    assert cs.credible_set([]) == []


# --- locus labels -----------------------------------------------------------


def test_index_variants_within_the_cojo_window_share_a_locus():
    rows = cs.prepare_sumstats([
        _rec(1_000_000, 1e-9, rsid="rs1"), _rec(2_500_000, 1e-9, rsid="rs2"),
        _rec(3_900_000, 1e-9, rsid="rs3"), _rec(9_000_000, 1e-9, rsid="rs4")])
    labels = cs.merge_index_variants_into_loci(rows)
    assert labels["rs1"] == labels["rs2"] == labels["rs3"] == "chr9:1.0-3.9Mb"
    assert labels["rs4"] == "chr9:9.0-9.0Mb"


def test_index_variants_farther_than_the_window_split():
    rows = cs.prepare_sumstats([_rec(1_000_000, 1e-9, rsid="rs1"), _rec(3_000_001, 1e-9, rsid="rs2")])
    labels = cs.merge_index_variants_into_loci(rows)
    assert labels["rs1"] != labels["rs2"]


# --- derive_credible_sets: records in, portal-shaped rows out ---------------


def _two_signal_records():
    return [
        _rec(1_000_000, 1e-12, rsid="rs1", beta=0.1),
        _rec(1_000_500, 1e-8, rsid="rs1b", beta=0.08),      # tag of rs1
        _rec(1_300_000, 1e-10, rsid="rs2", beta=-0.05),
        _rec(2_700_000, 1e-4, rsid="rs3", beta=0.01),       # cojo window of both, fm window of neither
        _rec(9_000_000, 1e-3, rsid="rs4", beta=0.01),       # outside every window
        _rec(500, 1e-9, chrom="2"),                          # rsID-less: unusable
    ]


def test_two_index_variants_give_two_sets_conditioned_on_each_other():
    recs = _two_signal_records()
    index = cs.prepare_sumstats([recs[0], recs[2]])
    # rs1b's conditional p collapses once rs1 is accounted for; rs1 stays strong.
    gcta = _gcta_stub(jma=_jma(index), cond_stats={"rs1b": (0.001, 0.02, 0.9), "rs2": (-0.05, 0.01, 1e-10)})

    variants, sets_ = cs.derive_credible_sets(recs, "guidX", "ds", gcta=gcta, ancestry="EUR")

    assert gcta.slct_calls == [("9", ["rs1", "rs1b", "rs2"])]
    assert gcta.panel_events == [("ensure", "9"), ("release", "9")]
    cond_by_index = {tuple(c[2]): c[1] for c in gcta.cond_calls}
    assert cond_by_index[("rs2",)] == ["rs1", "rs1b", "rs2", "rs3"]     # rs1's window
    assert cond_by_index[("rs1",)] == ["rs1", "rs1b", "rs2", "rs3"]     # rs2's window

    assert [s["credibleSetId"] for s in sets_] == ["chr9:1000000 rs1", "chr9:1300000 rs2"]
    s1 = sets_[0]
    assert s1["method"] == cs.METHOD and s1["source"] == "sifter-cojo"
    assert s1["locus"] == "chr9:1.0-1.3Mb" and s1["ancestry"] == "EUR"
    assert (s1["leadVarId"], s1["leadPosition"]) == ("9:1000000:T:C", 1_000_000)
    assert (s1["start"], s1["end"]) == (1_000_000, 1_000_001)
    assert s1["phenotype"] == "guidX" and s1["dataset"] == "ds" and s1["chromosome"] == "9"

    set1 = [v for v in variants if v["credibleSetId"] == "chr9:1000000 rs1"]
    assert [v["dbSNP"] for v in set1] == ["rs1"]            # rs1b conditioned away
    v = set1[0]
    assert v["leadSNP"] is True and v["alignment"] == 1.0
    assert (v["betaConditioned"], v["stdErrConditioned"], v["pValueConditioned"]) == (0.1, 0.01, 1e-12)
    assert v["posteriorProbability"] == pytest.approx(1.0) and v["in95CredibleSet"] and v["in99CredibleSet"]
    assert v["posteriorCumulative"] == pytest.approx(1.0) and v["logABF"] > 0
    assert v["source"] == "sifter-cojo" and v["ancestry"] == "EUR"
    assert v["varId"] == "9:1000000:T:C" and v["eaf"] == 0.3 and v["n"] == 20000.0

    set2 = [v for v in variants if v["credibleSetId"] == "chr9:1300000 rs2"]
    assert [v["dbSNP"] for v in set2] == ["rs2"]
    assert set2[0]["alignment"] == 1.0                        # sign vs its own lead


def test_a_lone_index_variant_uses_marginal_statistics_without_conditioning():
    # rs1 is the only genome-wide-significant variant; rs1b just misses and
    # is comparable enough to share the 95% set.
    recs = [_rec(1_000_000, 4e-8, rsid="rs1", beta=0.1), _rec(1_000_500, 6e-8, rsid="rs1b", beta=-0.08)]
    gcta = _gcta_stub()
    variants, sets_ = cs.derive_credible_sets(recs, "guidX", "ds", gcta=gcta)

    assert gcta.slct_calls == [] and gcta.cond_calls == []   # one GWS variant, no GCTA at all
    assert len(sets_) == 1 and "ancestry" not in sets_[0]
    by_rsid = {v["dbSNP"]: v for v in variants}
    assert set(by_rsid) == {"rs1", "rs1b"}
    assert by_rsid["rs1"]["pValueConditioned"] == 4e-8 and by_rsid["rs1"]["leadSNP"] is True
    assert by_rsid["rs1b"]["alignment"] == -1.0 and by_rsid["rs1b"]["leadSNP"] is False


def test_sets_are_ordered_by_chromosome_then_lead_position():
    recs = [_rec(5_000_000, 1e-9, rsid="rsX", chrom="X"), _rec(7_000_000, 1e-9, rsid="rs2", chrom="2"),
            _rec(1_000_000, 1e-9, rsid="rs1", chrom="10")]
    _, sets_ = cs.derive_credible_sets(recs, "guidX", "ds", gcta=_gcta_stub())
    assert [s["credibleSetId"] for s in sets_] == ["chr2:7000000 rs2", "chr10:1000000 rs1", "chrX:5000000 rsX"]


def test_no_gws_signal_yields_empty_outputs_and_skips_gcta():
    gcta = _gcta_stub()
    assert cs.derive_credible_sets([_rec(100, 1e-4, rsid="rs1")], "guidX", "ds", gcta=gcta) == ([], [])
    assert gcta.slct_calls == [] and gcta.panel_events == []


def test_missing_eaf_or_n_skips_derivation_with_a_log_line(capsys):
    gcta = _gcta_stub()
    assert cs.derive_credible_sets([_rec(100, 1e-9, rsid="rs1", eaf=None)], "guidX", "ds", gcta=gcta) == ([], [])
    assert cs.derive_credible_sets([_rec(100, 1e-9, rsid="rs1", n=None)], "guidX", "ds", gcta=gcta) == ([], [])
    assert gcta.slct_calls == []
    assert capsys.readouterr().out.count("skipping derived credible sets") == 2


def test_rsid_lookup_fills_missing_rsids_before_gcta():
    recs = [_rec(1_000_000, 1e-12), _rec(1_300_000, 1e-10, rsid="rs2")]
    lookup = MagicMock(return_value={"9:1000000:T:C": "rs1"})
    filled = cs.prepare_sumstats([dict(recs[0], dbSNP="rs1"), recs[1]])
    gcta = _gcta_stub(jma=_jma(filled))
    _, sets_ = cs.derive_credible_sets(recs, "guidX", "ds", gcta=gcta, rsid_lookup=lookup)
    lookup.assert_called_once_with({"9:1000000:T:C"})
    assert gcta.slct_calls == [("9", ["rs1", "rs2"])]
    assert [s["credibleSetId"] for s in sets_] == ["chr9:1000000 rs1", "chr9:1300000 rs2"]


def test_an_index_without_a_conditional_report_gets_no_set(capsys):
    recs = [_rec(1_000_000, 1e-12, rsid="rs1"), _rec(1_300_000, 1e-10, rsid="rs2")]
    gcta = _gcta_stub(jma=_jma(cs.prepare_sumstats(recs)), cma=None)
    variants, sets_ = cs.derive_credible_sets(recs, "guidX", "ds", gcta=gcta)
    assert (variants, sets_) == ([], [])
    assert "no conditional GCTA output" in capsys.readouterr().out


def test_gcta_without_panel_hooks_is_accepted():
    class Bare:
        def slct(self, chrom, rows):
            return None

        def cond(self, chrom, rows, cond):
            return None
    _, sets_ = cs.derive_credible_sets([_rec(100, 1e-9, rsid="rs1")], "guidX", "ds", gcta=Bare())
    assert len(sets_) == 1


# --- GctaRunner: argv construction, files, panel lifecycle ------------------


def _fake_gcta_run(report_ext, report_text, rc=0, log_text=""):
    """A subprocess.run stand-in writing the report next to `--out`."""
    def run(argv, **kw):
        out = argv[argv.index("--out") + 1]
        if log_text:
            with open(out + ".log", "w") as f:
                f.write(log_text)
        if report_text is not None:
            with open(out + report_ext, "w") as f:
                f.write(report_text)
        return MagicMock(returncode=rc, args=argv)
    return run


def test_runner_slct_builds_the_reference_command_and_returns_the_jma(tmp_path):
    runner = cs.GctaRunner(workdir=str(tmp_path), gcta_bin="/bin/gcta")
    rows = cs.prepare_sumstats([_rec(100, 1e-9, rsid="rs1"), _rec(200, 1e-10, rsid="rs2")])
    seen = {}

    def run(argv, **kw):
        seen["argv"] = argv
        seen["ma"] = open(argv[argv.index("--cojo-file") + 1]).read()
        seen["snplist"] = open(argv[argv.index("--extract") + 1]).read()
        return _fake_gcta_run(".jma.cojo", "JMA")(argv, **kw)

    with patch.object(cs.subprocess, "run", side_effect=run):
        assert runner.slct("9", rows) == "JMA"

    argv = seen["argv"]
    assert argv[0] == "/bin/gcta"
    assert argv[argv.index("--bfile") + 1] == str(tmp_path / "panel" / "1000G.EUR.QC.9")
    assert argv[argv.index("--chr") + 1] == "9"
    for flag, value in (("--maf", "0.01"), ("--cojo-p", "5e-08"), ("--cojo-wind", "2000"),
                        ("--cojo-collinear", "0.9")):
        assert argv[argv.index(flag) + 1] == value
    assert "--cojo-slct" in argv and "--cojo-cond" not in argv
    assert seen["ma"].splitlines()[0] == "SNP\tA1\tA2\tfreq\tb\tse\tp\tN"
    assert seen["snplist"] == "rs1\nrs2\n"
    assert list(tmp_path.glob("gcta-*")) == []          # scratch dir cleaned up


def test_runner_cond_passes_the_condition_list_and_returns_the_cma(tmp_path):
    runner = cs.GctaRunner(workdir=str(tmp_path), gcta_bin="/bin/gcta")
    rows = cs.prepare_sumstats([_rec(100, 1e-9, rsid="rs1"), _rec(200, 1e-3, rsid="rs2")])
    seen = {}

    def run(argv, **kw):
        seen["argv"] = argv
        seen["cond"] = open(argv[argv.index("--cojo-cond") + 1]).read()
        return _fake_gcta_run(".cma.cojo", "CMA")(argv, **kw)

    with patch.object(cs.subprocess, "run", side_effect=run):
        assert runner.cond("9", rows, ["rs2"]) == "CMA"
    assert seen["cond"] == "rs2\n"
    assert "--cojo-slct" not in seen["argv"] and "--maf" not in seen["argv"]


def test_runner_reports_gcta_errors_and_returns_none_without_a_report(tmp_path, capsys):
    runner = cs.GctaRunner(workdir=str(tmp_path), gcta_bin="/bin/gcta")
    rows = cs.prepare_sumstats([_rec(100, 1e-9, rsid="rs1")])
    with patch.object(cs.subprocess, "run",
                      side_effect=_fake_gcta_run(".jma.cojo", None, rc=1, log_text="ok\nError: boom\n")):
        assert runner.slct("9", rows) is None
    out = capsys.readouterr().out
    assert "GCTA exited 1" in out and "Error: boom" in out


def test_runner_never_uses_the_shell(tmp_path):
    runner = cs.GctaRunner(workdir=str(tmp_path), gcta_bin="/bin/gcta")
    rows = cs.prepare_sumstats([_rec(100, 1e-9, rsid="rs1")])
    with patch.object(cs.subprocess, "run", side_effect=_fake_gcta_run(".jma.cojo", "x")) as run:
        runner.slct("9", rows)
    assert isinstance(run.call_args.args[0], list)
    assert not run.call_args.kwargs.get("shell")


def test_runner_downloads_the_panel_once_and_releases_it(tmp_path):
    runner = cs.GctaRunner(bucket="assets", workdir=str(tmp_path))
    s3 = MagicMock()
    s3.download_file.side_effect = lambda b, k, dest: open(dest, "w").close()
    runner._s3 = s3

    prefix = runner.ensure_panel("4")
    runner.ensure_panel("4")
    keys = sorted(c.args[1] for c in s3.download_file.call_args_list)
    assert keys == ["cojo/bfiles/1000G.EUR.QC.4.bed", "cojo/bfiles/1000G.EUR.QC.4.bim",
                    "cojo/bfiles/1000G.EUR.QC.4.fam"]
    assert all(c.args[0] == "assets" for c in s3.download_file.call_args_list)
    assert all((tmp_path / "panel" / f"1000G.EUR.QC.4.{ext}").exists() for ext in ("bed", "bim", "fam"))
    assert prefix == str(tmp_path / "panel" / "1000G.EUR.QC.4")

    runner.release_panel("4")
    assert list((tmp_path / "panel").iterdir()) == []
    runner.release_panel("4")                            # idempotent


# --- write / clear the derived objects; indexing is run.py's job ------------


def test_write_derived_writes_both_objects_where_the_indexers_look():
    records = [_rec(500, 1e-9, rsid="rs1")]
    s3 = MagicMock()
    with patch.object(cs, "GctaRunner", return_value=_gcta_stub()), \
         patch.object(cs, "dbsnp_rsid_lookup", return_value={}):
        n = cs.write_derived_credible_sets(
            s3, "bkt", records, "guidX", dataset="d", ancestry="EUR", genome_build="GRCh37")

    assert n == 1
    writes = {kw["Key"]: kw["Body"] for _, kw in s3.put_object.call_args_list}
    assert set(writes) == {"credible-variants/guidX/variants.json",
                           "credible-sets/guidX/sets.json"}
    variant = json.loads(writes["credible-variants/guidX/variants.json"].decode().strip())
    assert variant["posteriorProbability"] == 1.0 and variant["source"] == "sifter-cojo"
    set_rec = json.loads(writes["credible-sets/guidX/sets.json"].decode().strip())
    assert (set_rec["start"], set_rec["end"], set_rec["method"]) == (500, 501, "COJO+ABF")


def test_write_derived_still_writes_empty_objects_without_a_signal():
    """No genome-wide-significant hit: write empty objects anyway, so the
    indexes run.py builds return cleanly instead of 404ing."""
    s3 = MagicMock()
    with patch.object(cs, "GctaRunner", return_value=_gcta_stub()), \
         patch.object(cs, "dbsnp_rsid_lookup", return_value={}):
        n = cs.write_derived_credible_sets(s3, "bkt", [_rec(100, 1e-4, rsid="rs1")], "guidX", dataset="d")

    assert n == 0
    bodies = [kw["Body"] for _, kw in s3.put_object.call_args_list]
    assert len(bodies) == 2 and all(b == b"" for b in bodies)


def test_clear_derived_writes_both_objects_empty():
    s3 = MagicMock()
    cs.clear_derived_credible_sets(s3, "bkt", "guidX")
    writes = {kw["Key"]: kw["Body"] for _, kw in s3.put_object.call_args_list}
    assert writes == {"credible-variants/guidX/variants.json": b"",
                      "credible-sets/guidX/sets.json": b""}
    assert all(kw["Bucket"] == "bkt" for _, kw in s3.put_object.call_args_list)


def test_na_conditional_stats_are_dropped_not_kept_as_strings():
    """GCTA writes `NA` for bC/bC_se/pC on the SNPs it conditioned on; the
    reference's inner join carried NaN through, which then broke the ABF.
    Those rows are dropped here (real-data regression, Vitamin D chr4)."""
    rows = [_rec(100, 1e-9, "rs1"), _rec(200, 1e-3, "rs2")]
    text = _CMA_HEADER + "\n" + "\t".join(map(str, [
        "4", "rs1", 100, "C", 0.3, 0.1, 0.01, 1e-9, 1000, 0.3, "NA", "NA", "NA"])) + "\n" \
        + "\t".join(map(str, ["4", "rs2", 200, "C", 0.3, 0.05, 0.01, 1e-3, 1000, 0.3, 0.04, 0.01, 6e-5])) + "\n"
    out = cs.conditional_stats(rows, text)
    assert [r["dbSNP"] for r in out] == ["rs2"]
    assert out[0]["p_cond"] == 6e-5
    parsed = cs.parse_cojo_table(text)
    assert parsed[0]["pC"] is None and parsed[1]["pC"] == 6e-5
