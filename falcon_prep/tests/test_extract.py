import io
import math
import pytest
from falcon_prep.columns import parse_metadata
from falcon_prep.extract import extract_significant, Variant, ExtractStats

META = {
    "ancestry": "EUR", "separator": "\t", "genome_build": "GRCh37",
    "effective_n": 1000.0,
    "col_map": {"chromosome": "chrom", "position": "pos", "reference": "ref",
                "alt": "alt", "beta": "beta", "se": "se"},
}

def _tsv(rows):
    return io.StringIO("\n".join("\t".join(r) for r in rows) + "\n")


def test_keeps_only_variants_above_threshold():
    fh = _tsv([
        ["chrom", "pos", "ref", "alt", "beta", "se", "rsid"],
        ["1", "100", "A", "G", "0.5", "0.1", "rs1"],   # z = 5.0 keep
        ["1", "200", "C", "T", "0.1", "0.1", "rs2"],   # z = 1.0 drop
    ])
    variants, stats, meta = extract_significant(fh, parse_metadata(META), 5.0)
    assert [v.rsid for v in variants] == ["rs1"]
    assert stats.total == 2
    assert stats.significant == 1


def test_detects_rsid_column_and_records_it():
    fh = _tsv([
        ["chrom", "pos", "ref", "alt", "beta", "se", "rs_id"],
        ["1", "100", "A", "G", "0.5", "0.1", "rs1"],
    ])
    _, _, meta = extract_significant(fh, parse_metadata(META), 5.0)
    assert meta.columns.rsid == "rs_id"


def test_uses_effective_n_when_no_n_column():
    fh = _tsv([
        ["chrom", "pos", "ref", "alt", "beta", "se"],
        ["1", "100", "A", "G", "0.5", "0.1"],
    ])
    variants, _, _ = extract_significant(fh, parse_metadata(META), 5.0)
    assert variants[0].n == 1000.0


def test_odds_ratio_is_log_transformed():
    meta = dict(META)
    meta["col_map"] = {"chromosome": "chrom", "position": "pos",
                       "reference": "ref", "alt": "alt",
                       "oddsRatio": "OR", "se": "se"}
    fh = _tsv([
        ["chrom", "pos", "ref", "alt", "OR", "se"],
        ["1", "100", "A", "G", "2.718281828", "0.1"],  # log(e) = 1.0, z = 10
    ])
    variants, _, _ = extract_significant(fh, parse_metadata(meta), 5.0)
    assert variants[0].beta == pytest.approx(1.0, abs=1e-6)


def test_skips_non_autosomal_and_unparseable_rows():
    fh = _tsv([
        ["chrom", "pos", "ref", "alt", "beta", "se"],
        ["X", "100", "A", "G", "0.5", "0.1"],       # sex chromosome
        ["1", "notanumber", "A", "G", "0.5", "0.1"],  # bad pos
        ["1", "100", "A", "G", "0.5", "0.1"],       # good
    ])
    variants, stats, _ = extract_significant(fh, parse_metadata(META), 5.0)
    assert len(variants) == 1
    assert stats.unparseable == 2


def test_strips_chr_prefix_from_chromosome():
    fh = _tsv([
        ["chrom", "pos", "ref", "alt", "beta", "se"],
        ["chr7", "100", "A", "G", "0.5", "0.1"],
    ])
    variants, _, _ = extract_significant(fh, parse_metadata(META), 5.0)
    assert variants[0].chrom == 7


def test_configured_rsid_column_wins_over_content_detection():
    meta = dict(META)
    meta["col_map"] = {**META["col_map"], "rsid": "MarkerName"}
    fh = _tsv([
        ["chrom", "pos", "ref", "alt", "beta", "se", "MarkerName"],
        ["1", "100", "A", "G", "0.5", "0.1", "rs1"],
    ])
    variants, _, m = extract_significant(fh, parse_metadata(meta), 5.0)
    assert m.columns.rsid == "MarkerName"
    assert variants[0].rsid == "rs1"


def test_falls_back_to_detection_when_configured_column_is_absent():
    meta = dict(META)
    meta["col_map"] = {**META["col_map"], "rsid": "NotInFile"}
    fh = _tsv([
        ["chrom", "pos", "ref", "alt", "beta", "se", "rsid"],
        ["1", "100", "A", "G", "0.5", "0.1", "rs1"],
    ])
    variants, _, m = extract_significant(fh, parse_metadata(meta), 5.0)
    assert m.columns.rsid == "rsid"
    assert variants[0].rsid == "rs1"
