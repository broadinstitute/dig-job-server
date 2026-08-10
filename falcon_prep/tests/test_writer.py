import os
import pytest
from falcon_prep.extract import Variant
from falcon_prep.writer import write_sumstats, SUMSTATS_HEADER


def _v(chrom, pos, rsid):
    return Variant(rsid=rsid, chrom=chrom, pos=pos, ref="A", alt="G",
                   beta=0.5, se=0.1, z=5.0, n=1000.0)


def test_writes_one_file_per_chromosome_present(tmp_path):
    counts = write_sumstats([_v(1, 100, "rs1"), _v(1, 200, "rs2"), _v(7, 300, "rs3")],
                            str(tmp_path))
    assert counts == {1: 2, 7: 1}
    assert os.path.exists(tmp_path / "1.sumstats")
    assert os.path.exists(tmp_path / "7.sumstats")
    assert not os.path.exists(tmp_path / "2.sumstats")


def test_header_matches_falcon_expectations(tmp_path):
    write_sumstats([_v(1, 100, "rs1")], str(tmp_path))
    header = (tmp_path / "1.sumstats").read_text().splitlines()[0].split("\t")
    assert tuple(header) == SUMSTATS_HEADER
    assert SUMSTATS_HEADER == ("rsID", "BETA", "SE", "Z", "CHROM", "POS", "REF", "ALT", "N")


def test_rows_are_sorted_by_position(tmp_path):
    write_sumstats([_v(1, 300, "rs3"), _v(1, 100, "rs1")], str(tmp_path))
    lines = (tmp_path / "1.sumstats").read_text().splitlines()[1:]
    assert [l.split("\t")[5] for l in lines] == ["100", "300"]


def test_values_round_trip(tmp_path):
    write_sumstats([_v(1, 100, "rs1")], str(tmp_path))
    row = (tmp_path / "1.sumstats").read_text().splitlines()[1].split("\t")
    assert row[0] == "rs1"
    assert float(row[1]) == 0.5
    assert float(row[3]) == 5.0
    assert row[4] == "1"


def test_empty_input_writes_nothing(tmp_path):
    assert write_sumstats([], str(tmp_path)) == {}
    assert list(tmp_path.iterdir()) == []


def test_embedded_tab_cannot_corrupt_the_row(tmp_path):
    v = Variant(rsid="rs1", chrom=1, pos=100, ref="A\tX", alt="G",
                beta=0.5, se=0.1, z=5.0, n=1000.0)
    write_sumstats([v], str(tmp_path))
    row = (tmp_path / "1.sumstats").read_text().splitlines()[1].split("\t")
    assert len(row) == 9
    assert row[6] == "AX"
    assert row[8] == "1000.0"
