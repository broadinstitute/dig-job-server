import pytest
from falcon_prep.columns import Columns, Metadata
from falcon_prep.extract import Variant
from falcon_prep.resolve import resolve, UnsupportedDataset

DBSNP = "dbSNP\tvarId\nrs100\t1:500:A:G\nrs200\t2:900:C:T\n"


@pytest.fixture
def dbsnp(tmp_path):
    p = tmp_path / "dbsnp.csv"
    p.write_text(DBSNP)
    return str(p)


def _meta(build, rsid_col):
    return Metadata(
        columns=Columns(chrom="c", pos="p", ref="r", alt="a", rsid=rsid_col),
        build=build, ancestry="EUR", effective_n=None, separator="\t",
    )


def _v(rsid, chrom, pos, ref="A", alt="G"):
    return Variant(rsid=rsid, chrom=chrom, pos=pos, ref=ref, alt=alt,
                   beta=0.5, se=0.1, z=5.0, n=1000.0)


def test_grch37_with_rsid_keeps_file_positions(dbsnp):
    out, stats = resolve([_v("rs100", 1, 500)], _meta("GRCh37", "rs_id"), dbsnp)
    assert out[0].rsid == "rs100"
    assert out[0].pos == 500
    assert stats.resolved == 1


def test_grch38_with_rsid_takes_position_from_dbsnp(dbsnp):
    # File says GRCh38 pos 817186; dbSNP says GRCh37 pos 500.
    out, _ = resolve([_v("rs100", 1, 817186)], _meta("GRCh38", "rs_id"), dbsnp)
    assert out[0].pos == 500


def test_grch37_without_rsid_reverse_looks_up_by_varid(dbsnp):
    out, _ = resolve([_v(None, 1, 500, "A", "G")], _meta("GRCh37", None), dbsnp)
    assert out[0].rsid == "rs100"


def test_reverse_lookup_tries_flipped_alleles(dbsnp):
    out, _ = resolve([_v(None, 1, 500, "G", "A")], _meta("GRCh37", None), dbsnp)
    assert out[0].rsid == "rs100"


def test_unresolvable_variants_are_dropped_and_counted(dbsnp):
    out, stats = resolve(
        [_v("rs100", 1, 500), _v("rs999", 1, 700)], _meta("GRCh37", "rs_id"), dbsnp
    )
    assert [v.rsid for v in out] == ["rs100"]
    assert stats.needed == 2
    assert stats.resolved == 1


def test_grch38_without_rsid_is_rejected(dbsnp):
    with pytest.raises(UnsupportedDataset, match="GRCh38"):
        resolve([_v(None, 1, 500)], _meta("GRCh38", None), dbsnp)


def test_unknown_build_is_rejected(dbsnp):
    with pytest.raises(UnsupportedDataset, match="build"):
        resolve([_v("rs100", 1, 500)], _meta("GRCh36", "rs_id"), dbsnp)


def test_duplicate_rsids_are_deduped_keeping_largest_abs_z(dbsnp):
    a = _v("rs100", 1, 500); a.z = 5.0
    b = _v("rs100", 1, 500); b.z = -9.0
    out, stats = resolve([a, b], _meta("GRCh37", "rs_id"), dbsnp)
    assert len(out) == 1
    assert out[0].z == -9.0
    assert stats.resolved == 1
    assert stats.duplicates == 1
