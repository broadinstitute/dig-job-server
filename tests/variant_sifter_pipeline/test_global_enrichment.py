import json
from unittest.mock import MagicMock

from variant_sifter_pipeline import index_build
from variant_sifter_pipeline.global_enrichment import (
    build_global_enrichment, write_global_enrichment)

GUID = "g1"


def test_record_has_spec_shape():
    recs = build_global_enrichment(["Adipose\tAdipose_tissue\tbiosample1\t2.5\t0.01"],
                                   GUID, "EU")
    assert recs == [{"phenotype": GUID, "ancestry": "EU", "annotation": "Adipose",
                     "tissue": "Adipose_tissue", "biosample": "biosample1",
                     "SNPs": 2.5, "expectedSNPs": 1, "pValue": 0.01}]


def test_unparseable_short_and_blank_lines_are_skipped():
    lines = ["a\tt\tb\t2.0\tNA", "a\tt\t2.0\t0.1", "", "   ", "a\tt\tb\t1.5\t0.2"]
    recs = build_global_enrichment(lines, GUID, "EU")
    assert len(recs) == 1 and recs[0]["SNPs"] == 1.5


def test_non_finite_numbers_are_skipped():
    assert build_global_enrichment(["a\tt\tb\tinf\t0.1", "a\tt\tb\t1\tnan"], GUID, "EU") == []


def test_empty_biosample_is_kept():
    recs = build_global_enrichment(["a\tt\t\t2.0\t0.1"], GUID, "EU")
    assert recs[0]["biosample"] == ""


def test_trailing_newline_is_tolerated():
    assert len(build_global_enrichment(["a\tt\tb\t2.0\t0.1\n"], GUID, "EU")) == 1


def test_ancestry_none():
    recs = build_global_enrichment(["a\tt\tb\t2.0\t0.1"], GUID, None)
    assert recs[0]["ancestry"] is None


def test_empty_input():
    assert build_global_enrichment([], GUID, "EU") == []


def test_write_puts_json_lines_at_key():
    s3 = MagicMock()
    recs = build_global_enrichment(["a\tt\tb\t2.0\t0.1", "c\tu\td\t3.0\t0.2"], GUID, "EU")
    write_global_enrichment(s3, "bkt", recs, GUID)
    kw = s3.put_object.call_args.kwargs
    assert kw["Bucket"] == "bkt"
    assert kw["Key"] == index_build.global_enrichment_key(GUID)
    lines = kw["Body"].decode().splitlines()
    assert [json.loads(l) for l in lines] == recs


def test_write_empty_list_writes_empty_body():
    s3 = MagicMock()
    write_global_enrichment(s3, "bkt", [], GUID)
    assert s3.put_object.call_args.kwargs["Body"] == b""
