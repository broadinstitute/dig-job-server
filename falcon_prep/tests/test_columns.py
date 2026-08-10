import pytest
from falcon_prep.columns import Columns, Metadata, parse_metadata, detect_rsid_column


def test_parse_metadata_maps_job_server_col_map():
    meta = {
        "ancestry": "EUR",
        "separator": "\t",
        "genome_build": "GRCh37",
        "effective_n": 342499.0,
        "col_map": {
            "chromosome": "#chrom", "position": "pos",
            "reference": "ref", "alt": "alt",
            "beta": "beta", "pValue": "pval",
        },
    }
    m = parse_metadata(meta)
    assert m.build == "GRCh37"
    assert m.ancestry == "EUR"
    assert m.effective_n == 342499.0
    assert m.columns.chrom == "#chrom"
    assert m.columns.pos == "pos"
    assert m.columns.beta == "beta"
    assert m.columns.pvalue == "pval"
    assert m.columns.se is None


def test_parse_metadata_maps_odds_ratio():
    meta = {
        "ancestry": "EUR", "separator": "\t", "genome_build": "GRCh37",
        "effective_n": None,
        "col_map": {"chromosome": "CHR", "position": "BP", "alt": "A1",
                    "reference": "A2", "oddsRatio": "OR", "pValue": "P"},
    }
    m = parse_metadata(meta)
    assert m.columns.odds_ratio == "OR"
    assert m.columns.beta is None


def test_parse_metadata_reads_rsid_and_se_when_the_upload_recorded_them():
    # Current uploads carry these keys (job_server/falcon.py::COLMAP_TO_SUMSTATS);
    # historical ones do not, hence the content-based fallback in Task 3.
    meta = {
        "ancestry": "EUR", "separator": "\t", "genome_build": "GRCh37",
        "effective_n": None,
        "col_map": {"chromosome": "CHR", "position": "BP", "alt": "A1",
                    "reference": "A2", "beta": "B", "se": "SE", "rsid": "SNP"},
    }
    m = parse_metadata(meta)
    assert m.columns.se == "SE"
    assert m.columns.rsid == "SNP"


def test_detect_rsid_by_content_not_name():
    # `variant_id` holds chr:pos:ref:alt here; `rs_id` holds the real rsIDs.
    header = ["chromosome", "variant_id", "rs_id", "beta"]
    rows = [
        ["1", "1:10419:C:T", "rs914488949", "0.1"],
        ["1", "1:10429:G:C", "rs555500075", "0.2"],
    ]
    assert detect_rsid_column(header, rows) == "rs_id"


def test_detect_rsid_accepts_variant_id_when_it_holds_rsids():
    header = ["chromosome", "variant_id", "beta"]
    rows = [["1", "rs3094315", "0.1"], ["1", "rs3131972", "0.2"]]
    assert detect_rsid_column(header, rows) == "variant_id"


def test_detect_rsid_returns_none_when_absent():
    header = ["chromosome", "position", "other_allele", "effect_allele", "beta"]
    rows = [["1", "10419", "C", "T", "0.1"]]
    assert detect_rsid_column(header, rows) is None


def test_detect_rsid_ignores_column_with_mostly_missing_values():
    header = ["chromosome", "rsid", "beta"]
    rows = [["1", "NA", "0.1"], ["1", "NA", "0.2"], ["1", "rs123", "0.3"]]
    assert detect_rsid_column(header, rows) is None
