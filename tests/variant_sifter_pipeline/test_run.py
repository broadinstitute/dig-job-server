import gzip
import io
import json
from unittest.mock import MagicMock, patch

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

    with patch.object(run_mod.boto3, "client", return_value=s3), \
         patch.object(run_mod, "index_associations") as idx:
        n = run_mod.run("u", "d", "guidX")

    assert n == 1                                  # rs1 kept, rs2 filtered out
    idx.assert_called_once()

    _, kwargs = s3.put_object.call_args
    assert kwargs["Key"] == "associations/guidX.json"
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
         patch.object(run_mod, "index_associations"):
        n = run_mod.run("u", "d", "guidG")

    assert n == 1
    _, kwargs = s3.put_object.call_args
    rec = json.loads(kwargs["Body"].decode().strip())
    assert (rec["chromosome"], rec["position"]) == ("8", 100)
    assert rec["pValue"] == 1e-9
