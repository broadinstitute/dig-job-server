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


# ---- S3 sync -----------------------------------------------------------------

import gzip
import io
import json
from unittest.mock import MagicMock

META = {"name": "SuSiE v1", "slug": "susie-v1", "file": "cs.tsv", "separator": "\t",
        "col_map": {"chromosome": "CHR", "position": "POS", "reference": "REF", "alt": "ALT",
                    "credibleSetId": "CS", "posteriorProbability": "PIP", "beta": "B"},
        "uploaded_at": "2026-09-03T12:00:00"}
CS_TSV = b"CHR\tPOS\tREF\tALT\tCS\tPIP\tB\n1\t100\tA\tG\t1\t0.6\t0.1\n1\t200\tC\tT\t1\t0.4\t-0.2\n"
UP = "userdata/u/genetic/d/credible_sets/"


def _fake_s3(objects: dict):
    """A MagicMock S3 whose list/get answer from `objects` ({key: bytes})."""
    s3 = MagicMock()

    def paginate(Bucket, Prefix):
        return [{"Contents": [{"Key": k} for k in sorted(objects) if k.startswith(Prefix)]}]

    s3.get_paginator.return_value.paginate.side_effect = paginate
    s3.get_object.side_effect = lambda Bucket, Key: {"Body": io.BytesIO(objects[Key])}
    return s3


class _Genome:
    """base_at answers from a dict; anything else is 'no reference base'."""

    def __init__(self, bases):
        self.bases = bases

    def base_at(self, chromosome, position):
        return self.bases.get((chromosome, position))


def test_list_upload_metadata_reads_only_metadata_objects():
    s3 = _fake_s3({
        f"{UP}susie-v1/raw/metadata": json.dumps(META).encode(),
        f"{UP}susie-v1/raw/cs.tsv": CS_TSV,
        f"{UP}finemap/raw/metadata": json.dumps({**META, "slug": "finemap", "name": "FINEMAP"}).encode(),
    })
    metas = ucs.list_upload_metadata(s3, "bkt", "u", "d")
    assert [m["slug"] for m in metas] == ["finemap", "susie-v1"]


def test_read_upload_rows_handles_gzip_by_content_not_by_name():
    s3 = _fake_s3({f"{UP}susie-v1/raw/cs.tsv": gzip.compress(CS_TSV)})
    rows = list(ucs.read_upload_rows(s3, "bkt", "u", "d", META))
    assert [r["POS"] for r in rows] == ["100", "200"]


def test_sync_writes_both_objects_per_upload_and_reports_counts():
    s3 = _fake_s3({f"{UP}susie-v1/raw/metadata": json.dumps(META).encode(),
                   f"{UP}susie-v1/raw/cs.tsv": CS_TSV})
    counts = ucs.sync_uploaded_credible_sets(s3, "bkt", "bio", "u", "d", "guidX", ancestry="EUR")
    assert counts == {"susie-v1": {"variants": 2, "sets": 1}}
    writes = {kw["Key"]: kw for _, kw in s3.put_object.call_args_list}
    assert set(writes) == {"credible-variants/guidX/upload-susie-v1.json",
                           "credible-sets/guidX/upload-susie-v1.json"}
    assert all(kw["Bucket"] == "bio" for kw in writes.values())
    variants = [json.loads(l) for l in writes["credible-variants/guidX/upload-susie-v1.json"]["Body"].decode().splitlines()]
    assert [v["varId"] for v in variants] == ["1:100:A:G", "1:200:C:T"]
    assert variants[0]["leadSNP"] is True and variants[0]["alignment"] == 1.0 and variants[1]["alignment"] == -1.0
    set_rec = json.loads(writes["credible-sets/guidX/upload-susie-v1.json"]["Body"].decode().strip())
    assert set_rec["uploadName"] == "SuSiE v1" and set_rec["ancestry"] == "EUR"


def test_sync_orients_alleles_and_keeps_var_ids_and_alignment_consistent():
    """Reference base at 1:100 is G, so the upload's REF=A/ALT=G is flipped:
    alleles swap, beta negates, varId follows, alignment is recomputed."""
    s3 = _fake_s3({f"{UP}susie-v1/raw/metadata": json.dumps(META).encode(),
                   f"{UP}susie-v1/raw/cs.tsv": CS_TSV})
    genome = _Genome({("1", 100): "G", ("1", 200): "C"})
    ucs.sync_uploaded_credible_sets(s3, "bkt", "bio", "u", "d", "guidX", genome=genome)
    body = next(kw["Body"] for _, kw in s3.put_object.call_args_list
                if kw["Key"].startswith("credible-variants/"))
    variants = [json.loads(l) for l in body.decode().splitlines()]
    flipped = next(v for v in variants if v["position"] == 100)
    kept = next(v for v in variants if v["position"] == 200)
    assert (flipped["reference"], flipped["alt"], flipped["varId"], flipped["beta"]) == ("G", "A", "1:100:G:A", -0.1)
    assert (kept["reference"], kept["alt"], kept["beta"]) == ("C", "T", -0.2)
    # lead (pos 100) beta is now -0.1; pos 200 beta -0.2 -> same sign -> aligned
    assert flipped["alignment"] == 1.0 and kept["alignment"] == 1.0


def test_sync_deletes_objects_of_uploads_that_no_longer_exist():
    s3 = _fake_s3({
        f"{UP}susie-v1/raw/metadata": json.dumps(META).encode(),
        f"{UP}susie-v1/raw/cs.tsv": CS_TSV,
        "credible-sets/guidX/sets.json": b"", "credible-variants/guidX/variants.json": b"",
        "credible-sets/guidX/upload-gone.json": b"", "credible-variants/guidX/upload-gone.json": b"",
        "credible-sets/guidX/upload-susie-v1.json": b"",
    })
    counts = ucs.sync_uploaded_credible_sets(s3, "bkt", "bio", "u", "d", "guidX")
    deleted = {kw["Key"] for _, kw in s3.delete_object.call_args_list}
    assert deleted == {"credible-sets/guidX/upload-gone.json", "credible-variants/guidX/upload-gone.json"}
    assert counts["gone"] == "removed"


def test_sync_with_no_uploads_writes_nothing_and_touches_no_derived_objects():
    s3 = _fake_s3({"credible-sets/guidX/sets.json": b"", "credible-variants/guidX/variants.json": b""})
    assert ucs.sync_uploaded_credible_sets(s3, "bkt", "bio", "u", "d", "guidX") == {}
    s3.put_object.assert_not_called()
    s3.delete_object.assert_not_called()
