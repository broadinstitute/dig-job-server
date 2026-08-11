import gzip
import json
import pytest
from falcon_prep.cli import EXIT_NO_VARIANTS, EXIT_UNSUPPORTED, main

META = {
    "name": "t", "file": "g.tsv.gz", "ancestry": "EUR", "separator": "\t",
    "genome_build": "GRCh37", "phenotype": None, "effective_n": 1000.0,
    "col_map": {"chromosome": "chrom", "position": "pos", "reference": "ref",
                "alt": "alt", "beta": "beta", "se": "se"},
}
ROWS = [
    ["chrom", "pos", "ref", "alt", "beta", "se", "rsid"],
    ["1", "500", "A", "G", "0.5", "0.1", "rs100"],     # z=5.0 keep
    ["2", "900", "C", "T", "0.1", "0.1", "rs200"],     # z=1.0 drop
]
DBSNP = "dbSNP\tvarId\nrs100\t1:500:A:G\nrs200\t2:900:C:T\n"


@pytest.fixture
def workspace(tmp_path):
    raw = tmp_path / "raw"; raw.mkdir()
    (raw / "metadata").write_text(json.dumps(META))
    with gzip.open(raw / "g.tsv.gz", "wt") as fh:
        fh.write("\n".join("\t".join(r) for r in ROWS) + "\n")
    (tmp_path / "dbsnp.csv").write_text(DBSNP)
    return tmp_path


def test_writes_sumstats_and_reports_counts(workspace, capsys):
    rc = main([
        "--raw-dir", str(workspace / "raw"),
        "--out-dir", str(workspace / "sumstats"),
        "--dbsnp", str(workspace / "dbsnp.csv"),
        "--z-threshold", "5.0",
    ])
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"]["total"] == 2
    assert summary["counts"]["significant"] == 1
    assert summary["counts"]["resolved"] == 1
    assert summary["chromosomes"] == {"1": 1}
    assert (workspace / "sumstats" / "1.sumstats").exists()


def test_prefers_the_upload_named_in_metadata_over_a_stray_file(workspace, capsys):
    # A stray file sorting before the real upload must not be read instead.
    (workspace / "raw" / "AAA_stray.txt").write_text("garbage\n")
    rc = main([
        "--raw-dir", str(workspace / "raw"),
        "--out-dir", str(workspace / "sumstats"),
        "--dbsnp", str(workspace / "dbsnp.csv"),
        "--z-threshold", "5.0",
    ])
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"]["total"] == 2
    assert summary["upload_file"] == "g.tsv.gz"


def test_rejects_non_eur_ancestry(workspace):
    meta = dict(META); meta["ancestry"] = "AFR"
    (workspace / "raw" / "metadata").write_text(json.dumps(meta))
    rc = main(["--raw-dir", str(workspace / "raw"),
               "--out-dir", str(workspace / "s"),
               "--dbsnp", str(workspace / "dbsnp.csv")])
    assert rc == EXIT_UNSUPPORTED


def test_rejects_grch38_without_rsid(workspace):
    meta = dict(META); meta["genome_build"] = "GRCh38"
    (workspace / "raw" / "metadata").write_text(json.dumps(meta))
    rows = [r[:-1] for r in ROWS]  # drop the rsid column
    with gzip.open(workspace / "raw" / "g.tsv.gz", "wt") as fh:
        fh.write("\n".join("\t".join(r) for r in rows) + "\n")
    rc = main(["--raw-dir", str(workspace / "raw"),
               "--out-dir", str(workspace / "s"),
               "--dbsnp", str(workspace / "dbsnp.csv")])
    assert rc == EXIT_UNSUPPORTED


def test_fails_when_no_variants_survive(workspace):
    rc = main(["--raw-dir", str(workspace / "raw"),
               "--out-dir", str(workspace / "s"),
               "--dbsnp", str(workspace / "dbsnp.csv"),
               "--z-threshold", "50"])
    assert rc == EXIT_NO_VARIANTS


def test_missing_metadata_exits_unsupported(workspace, capsys):
    (workspace / "raw" / "metadata").unlink()
    rc = main(["--raw-dir", str(workspace / "raw"),
               "--out-dir", str(workspace / "s"),
               "--dbsnp", str(workspace / "dbsnp.csv")])
    assert rc == EXIT_UNSUPPORTED
    assert "metadata" in capsys.readouterr().err


def test_malformed_metadata_exits_unsupported(workspace, capsys):
    (workspace / "raw" / "metadata").write_text("{not json")
    rc = main(["--raw-dir", str(workspace / "raw"),
               "--out-dir", str(workspace / "s"),
               "--dbsnp", str(workspace / "dbsnp.csv")])
    assert rc == EXIT_UNSUPPORTED
    assert "metadata" in capsys.readouterr().err


def test_metadata_that_is_not_an_object_exits_unsupported(workspace, capsys):
    (workspace / "raw" / "metadata").write_text("[1, 2, 3]")
    rc = main(["--raw-dir", str(workspace / "raw"),
               "--out-dir", str(workspace / "s"),
               "--dbsnp", str(workspace / "dbsnp.csv")])
    assert rc == EXIT_UNSUPPORTED
    assert "metadata" in capsys.readouterr().err


def test_contract_codes_do_not_collide_with_argparse(workspace, capsys):
    """argparse exits 2 on a usage error.

    If the contract reused 2, a harness passing a bad argument would be
    reported as "this dataset is unsupported", and a caller branching on the
    code would permanently mark a good dataset unusable.
    """
    assert EXIT_UNSUPPORTED != 2
    assert EXIT_NO_VARIANTS != 2
    with pytest.raises(SystemExit) as e:
        main(["--raw-dir", str(workspace / "raw"),
              "--out-dir", str(workspace / "s"),
              "--dbsnp", str(workspace / "dbsnp.csv"),
              "--z-threshold", "not-a-float"])
    assert e.value.code == 2


def test_unmapped_essential_columns_are_rejected_not_counted_as_thin(workspace, capsys):
    """A col_map that never matches the header must not read as 'no signal'."""
    meta = dict(META)
    meta["col_map"] = {**META["col_map"], "chromosome": "NoSuchColumn"}
    (workspace / "raw" / "metadata").write_text(json.dumps(meta))
    rc = main(["--raw-dir", str(workspace / "raw"),
               "--out-dir", str(workspace / "s"),
               "--dbsnp", str(workspace / "dbsnp.csv")])
    assert rc == EXIT_UNSUPPORTED
    err = capsys.readouterr().err
    assert "not present in the upload" in err
    assert "chromosome" in err
