import gzip
import io
import json
from unittest.mock import MagicMock, patch

import pytest

from variant_sifter_pipeline import run as run_mod


def _body(data: bytes) -> dict:
    return {"Body": io.BytesIO(data)}


def test_run_reads_upload_builds_writes_and_indexes():
    """run() reads the dataset's metadata + GWAS from S3, builds the filtered
    associations, writes them GUID-keyed, and triggers the in-process index."""
    meta = {
        "file": "gwas.tsv", "separator": "\t",
        "col_map": {"chromosome": "CHR", "position": "POS", "reference": "REF",
                    "alt": "ALT", "pValue": "P", "beta": "BETA", "se": "SE",
                    "rsid": "SNP"},
    }
    gwas = (b"CHR\tPOS\tREF\tALT\tP\tBETA\tSE\tSNP\n"
            b"8\t100\tA\tG\t1e-9\t0.1\t0.02\trs1\n"
            b"8\t200\tC\tT\t0.5\t0.01\t0.02\trs2\n")   # rs2 dropped (p>0.05)

    s3 = MagicMock()
    s3.get_object.side_effect = [_body(json.dumps(meta).encode()), _body(gwas)]

    # Orientation is exercised by test_run_orients_alleles below; these two cover
    # the read/build/write/index wiring and must not reach for a reference genome.
    # The credible-set step is stubbed for the same reason: unpatched it would
    # reach for real S3 clumping assets (its own wiring has dedicated tests).
    with patch.object(run_mod.boto3, "client", return_value=s3), \
         patch.object(run_mod, "ORIENT_ALLELES", False), \
         patch.object(run_mod, "list_upload_metadata", return_value=[]), \
         patch.object(run_mod, "write_derived_credible_sets"), \
         patch.object(run_mod, "sync_uploaded_credible_sets"), \
         patch.object(run_mod, "index_credible_sets"), \
         patch.object(run_mod, "index_credible_variants"), \
         patch.object(run_mod, "index_associations") as idx:
        n = run_mod.run("u", "d", "guidX")

    assert n == 1                                  # rs1 kept, rs2 filtered out
    idx.assert_called_once()

    _, kwargs = s3.put_object.call_args
    # Under the per-dataset layout the object lives in the dataset's own folder,
    # which is what bioindex indexes as a prefix.
    assert kwargs["Key"] == "associations/guidX/associations.json"
    rec = json.loads(kwargs["Body"].decode().strip())
    assert rec["phenotype"] == "guidX"
    assert rec["dbSNP"] == "rs1"
    assert rec["zScore"] == 5.0                    # 0.1 / 0.02


def test_run_decompresses_gzipped_upload():
    """Real uploads are gzipped (e.g. .tsv.gz); run() must decompress them."""
    meta = {
        "file": "gwas.tsv.gz", "separator": "\t",
        "col_map": {"chromosome": "CHR", "position": "POS", "reference": "A2",
                    "alt": "A1", "pValue": "P", "beta": "BETA"},
    }
    plain = (b"CHR\tPOS\tA2\tA1\tP\tBETA\n"
             b"8\t100\tA\tG\t1e-9\t0.1\n"
             b"8\t200\tC\tT\t0.5\t0.01\n")   # second row dropped (p>0.05)
    gzipped = gzip.compress(plain)

    s3 = MagicMock()
    s3.get_object.side_effect = [_body(json.dumps(meta).encode()), _body(gzipped)]

    with patch.object(run_mod.boto3, "client", return_value=s3), \
         patch.object(run_mod, "ORIENT_ALLELES", False), \
         patch.object(run_mod, "list_upload_metadata", return_value=[]), \
         patch.object(run_mod, "write_derived_credible_sets"), \
         patch.object(run_mod, "sync_uploaded_credible_sets"), \
         patch.object(run_mod, "index_credible_sets"), \
         patch.object(run_mod, "index_credible_variants"), \
         patch.object(run_mod, "index_associations"):
        n = run_mod.run("u", "d", "guidG")

    assert n == 1
    _, kwargs = s3.put_object.call_args
    rec = json.loads(kwargs["Body"].decode().strip())
    assert (rec["chromosome"], rec["position"]) == ("8", 100)
    assert rec["pValue"] == 1e-9


def test_run_builds_credible_sets_after_indexing_associations():
    """The same job that indexes associations also derives + indexes the
    dataset's credible sets, keyed by the same GUID."""
    meta = {
        "file": "gwas.tsv", "separator": "\t", "ancestry": "EU",
        "genome_build": "GRCh38",
        "col_map": {"chromosome": "CHR", "position": "POS", "reference": "REF",
                    "alt": "ALT", "pValue": "P"},
    }
    gwas = b"CHR\tPOS\tREF\tALT\tP\n8\t100\tA\tG\t1e-9\n"

    s3 = MagicMock()
    s3.get_object.side_effect = [_body(json.dumps(meta).encode()), _body(gwas)]

    with patch.object(run_mod.boto3, "client", return_value=s3), \
         patch.object(run_mod, "ORIENT_ALLELES", False), \
         patch.object(run_mod, "list_upload_metadata", return_value=[]), \
         patch.object(run_mod, "index_associations"), \
         patch.object(run_mod, "sync_uploaded_credible_sets"), \
         patch.object(run_mod, "index_credible_sets"), \
         patch.object(run_mod, "index_credible_variants"), \
         patch.object(run_mod, "clear_derived_credible_sets") as clear, \
         patch.object(run_mod, "write_derived_credible_sets") as cred:
        run_mod.run("u", "myGwas", "guidC")

    (s3_arg, bucket, records, guid), kwargs = cred.call_args
    assert (s3_arg, bucket, guid) == (s3, run_mod.GWAS_CE_BUCKET, "guidC")
    # genome_build picks the MHC coordinates the COJO port excludes.
    assert kwargs == {"dataset": "myGwas", "ancestry": "EU", "genome_build": "GRCh38"}
    assert [r["position"] for r in records] == [100]
    clear.assert_not_called()


def test_run_survives_a_credible_set_failure(capsys):
    """Credible sets are an enhancement: if derivation blows up (GCTA or LD
    panel missing, panel mismatch, ...), the associations index must still
    ship and the job must not fail."""
    meta = {
        "file": "gwas.tsv", "separator": "\t",
        "col_map": {"chromosome": "CHR", "position": "POS", "reference": "REF",
                    "alt": "ALT", "pValue": "P"},
    }
    gwas = b"CHR\tPOS\tREF\tALT\tP\n8\t100\tA\tG\t1e-9\n"

    s3 = MagicMock()
    s3.get_object.side_effect = [_body(json.dumps(meta).encode()), _body(gwas)]

    with patch.object(run_mod.boto3, "client", return_value=s3), \
         patch.object(run_mod, "ORIENT_ALLELES", False), \
         patch.object(run_mod, "list_upload_metadata", return_value=[]), \
         patch.object(run_mod, "index_associations") as idx, \
         patch.object(run_mod, "sync_uploaded_credible_sets"), \
         patch.object(run_mod, "index_credible_sets"), \
         patch.object(run_mod, "index_credible_variants"), \
         patch.object(run_mod, "write_derived_credible_sets",
                      side_effect=RuntimeError("no panel")):
        n = run_mod.run("u", "d", "guidF")

    assert n == 1
    idx.assert_called_once()
    assert "credible-set derivation failed" in capsys.readouterr().out


def test_run_orients_alleles_against_the_reference(tmp_path, monkeypatch):
    """The whole point of orientation, end to end through run(): the written
    record carries reference-genome allele order, and beta's sign follows alt."""
    meta = {
        "file": "gwas.tsv", "separator": "\t",
        "col_map": {"chromosome": "CHR", "position": "POS", "reference": "REF",
                    "alt": "ALT", "pValue": "P", "beta": "BETA", "se": "SE"},
    }
    # Reference base at 8:3 is G, so the upload's REF=A/ALT=G is reversed.
    gwas = (b"CHR\tPOS\tREF\tALT\tP\tBETA\tSE\n"
            b"8\t3\tA\tG\t1e-9\t0.4\t0.1\n")

    fasta = tmp_path / "ref.fasta"
    fasta.write_text(">8\nTTGAA\n")
    # contig, length, byte offset of the first base (past the 3-byte ">8\n"
    # header), bases per line, bytes per line.
    (tmp_path / "ref.fasta.fai").write_text("8\t5\t3\t5\t6\n")
    monkeypatch.setenv("VS_REFERENCE_FASTA", str(fasta))

    s3 = MagicMock()
    s3.get_object.side_effect = [_body(json.dumps(meta).encode()), _body(gwas)]

    with patch.object(run_mod.boto3, "client", return_value=s3), \
         patch.object(run_mod, "list_upload_metadata", return_value=[]), \
         patch.object(run_mod, "write_derived_credible_sets"), \
         patch.object(run_mod, "sync_uploaded_credible_sets"), \
         patch.object(run_mod, "index_credible_sets"), \
         patch.object(run_mod, "index_credible_variants"), \
         patch.object(run_mod, "index_associations"):
        run_mod.run("u", "d", "guidO")

    _, kwargs = s3.put_object.call_args
    rec = json.loads(kwargs["Body"].decode().strip())
    assert (rec["reference"], rec["alt"]) == ("G", "A")   # swapped to match reference
    assert rec["beta"] == -0.4                            # sign follows the new alt
    assert rec["stdErr"] == 0.1                           # direction-free, unchanged
    assert rec["pValue"] == 1e-9


# ---- modes -----------------------------------------------------------------

_META = {
    "file": "gwas.tsv", "separator": "\t", "ancestry": "EU",
    "col_map": {"chromosome": "CHR", "position": "POS", "reference": "REF",
                "alt": "ALT", "pValue": "P"},
}
_GWAS = b"CHR\tPOS\tREF\tALT\tP\n8\t100\tA\tG\t1e-9\n"


_UPLOAD = {"slug": "my-sets", "file": "sets.tsv"}


def _full_patches(s3, uploads=()):
    """Everything run() reaches for besides S3, stubbed. `uploads` is what the
    attached-upload listing returns (none by default)."""
    return (patch.object(run_mod.boto3, "client", return_value=s3),
            patch.object(run_mod, "ORIENT_ALLELES", False),
            patch.object(run_mod, "index_associations"),
            patch.object(run_mod, "write_derived_credible_sets", return_value=0),
            patch.object(run_mod, "sync_uploaded_credible_sets", return_value={}),
            patch.object(run_mod, "index_credible_sets"),
            patch.object(run_mod, "index_credible_variants"),
            patch.object(run_mod, "list_upload_metadata", return_value=list(uploads)),
            patch.object(run_mod, "clear_derived_credible_sets"))


def test_full_mode_syncs_uploads_then_indexes_credible_sets_once():
    s3 = MagicMock()
    s3.get_object.side_effect = [_body(json.dumps(_META).encode()), _body(_GWAS)]
    client, orient, idx_assoc, derived, sync, idx_sets, idx_vars, listing, clear = _full_patches(s3)
    with client, orient, idx_assoc, derived, sync as sync_mock, idx_sets as sets_mock, \
         idx_vars as vars_mock, listing as listing_mock, clear:
        run_mod.run("u", "d", "guidM")
    listing_mock.assert_called_once_with(s3, run_mod.USER_DATA_BUCKET, "u", "d")
    (s3_arg, up_bucket, bio_bucket, user, ds, guid), kwargs = sync_mock.call_args
    assert (s3_arg, up_bucket, bio_bucket, user, ds, guid) == \
        (s3, run_mod.USER_DATA_BUCKET, run_mod.GWAS_CE_BUCKET, "u", "d", "guidM")
    assert kwargs == {"ancestry": "EU", "genome": None}
    sets_mock.assert_called_once_with("guidM")
    vars_mock.assert_called_once_with("guidM")


def test_credible_sets_mode_skips_associations_and_derived_sets():
    s3 = MagicMock()
    s3.get_object.side_effect = [_body(json.dumps(_META).encode())]
    client, orient, idx_assoc, derived, sync, idx_sets, idx_vars, listing, clear = _full_patches(s3)
    with client, orient, idx_assoc as assoc_mock, derived as derived_mock, sync as sync_mock, \
         idx_sets as sets_mock, idx_vars as vars_mock, listing, clear as clear_mock:
        n = run_mod.run("u", "d", "guidC", mode="credible-sets")
    assert n == 0
    assoc_mock.assert_not_called()
    derived_mock.assert_not_called()
    clear_mock.assert_not_called()             # no uploads: derived objects untouched
    s3.put_object.assert_not_called()          # no associations written
    sync_mock.assert_called_once()
    sets_mock.assert_called_once_with("guidC")
    vars_mock.assert_called_once_with("guidC")


# ---- uploads win over derived sets -------------------------------------------


def test_full_mode_with_an_upload_clears_derived_sets_instead_of_deriving(capsys):
    """A dataset with the user's own credible sets attached gets no derived
    sets: the derived objects are written empty (so earlier derived rows drop
    out of the index), the upload is still synced, and the indexes still build."""
    s3 = MagicMock()
    s3.get_object.side_effect = [_body(json.dumps(_META).encode()), _body(_GWAS)]
    client, orient, idx_assoc, derived, sync, idx_sets, idx_vars, listing, clear = \
        _full_patches(s3, uploads=[_UPLOAD])
    with client, orient, idx_assoc, derived as derived_mock, sync as sync_mock, \
         idx_sets as sets_mock, idx_vars as vars_mock, listing, clear as clear_mock:
        n = run_mod.run("u", "d", "guidU")
    assert n == 1                                      # associations still built
    derived_mock.assert_not_called()
    clear_mock.assert_called_once_with(s3, run_mod.GWAS_CE_BUCKET, "guidU")
    sync_mock.assert_called_once()
    sets_mock.assert_called_once_with("guidU")
    vars_mock.assert_called_once_with("guidU")
    assert "skipping derived credible sets: 1 credible-set upload(s) attached" \
        in capsys.readouterr().out


def test_full_mode_without_uploads_derives():
    s3 = MagicMock()
    s3.get_object.side_effect = [_body(json.dumps(_META).encode()), _body(_GWAS)]
    client, orient, idx_assoc, derived, sync, idx_sets, idx_vars, listing, clear = _full_patches(s3)
    with client, orient, idx_assoc, derived as derived_mock, sync, idx_sets, idx_vars, \
         listing, clear as clear_mock:
        run_mod.run("u", "d", "guidD")
    derived_mock.assert_called_once()
    assert derived_mock.call_args.kwargs["genome_build"] is None   # _META has none
    clear_mock.assert_not_called()


def test_credible_sets_mode_with_an_upload_clears_derived_sets(capsys):
    """Attaching the first upload after a full run must drop the derived rows
    on that ingest, not wait for the next full run."""
    s3 = MagicMock()
    s3.get_object.side_effect = [_body(json.dumps(_META).encode())]
    client, orient, idx_assoc, derived, sync, idx_sets, idx_vars, listing, clear = \
        _full_patches(s3, uploads=[_UPLOAD, {**_UPLOAD, "slug": "other"}])
    with client, orient, idx_assoc, derived as derived_mock, sync as sync_mock, \
         idx_sets as sets_mock, idx_vars, listing, clear as clear_mock:
        run_mod.run("u", "d", "guidK", mode="credible-sets")
    derived_mock.assert_not_called()
    clear_mock.assert_called_once_with(s3, run_mod.GWAS_CE_BUCKET, "guidK")
    sync_mock.assert_called_once()
    sets_mock.assert_called_once_with("guidK")
    assert "cleared derived credible sets: 2 credible-set upload(s) attached" \
        in capsys.readouterr().out


def test_an_upload_sync_failure_fails_the_job():
    s3 = MagicMock()
    s3.get_object.side_effect = [_body(json.dumps(_META).encode()), _body(_GWAS)]
    client, orient, idx_assoc, derived, sync, idx_sets, idx_vars, listing, clear = _full_patches(s3)
    with client, orient, idx_assoc, derived, idx_sets as sets_mock, idx_vars, listing, clear, \
         patch.object(run_mod, "sync_uploaded_credible_sets", side_effect=RuntimeError("bad upload")):
        with pytest.raises(RuntimeError, match="bad upload"):
            run_mod.run("u", "d", "guidE")
    sets_mock.assert_not_called()


def test_unknown_mode_is_rejected_before_touching_aws():
    with patch.object(run_mod.boto3, "client") as client:
        with pytest.raises(ValueError):
            run_mod.run("u", "d", "g", mode="nope")
    client.assert_not_called()


def test_cli_accepts_mode(monkeypatch):
    calls = []
    monkeypatch.setattr(run_mod, "run", lambda *a, **kw: calls.append((a, kw)) or 0)
    run_mod.main(["--username", "u", "--dataset", "d", "--guid", "g", "--mode", "credible-sets"])
    assert calls == [(("u", "d", "g"), {"mode": "credible-sets"})]
    run_mod.main(["--username", "u", "--dataset", "d", "--guid", "g"])
    assert calls[-1] == (("u", "d", "g"), {"mode": "full"})
