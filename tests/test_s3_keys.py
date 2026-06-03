from job_server import s3


def test_get_gwas_s3_key_with_filename():
    assert (
        s3.get_gwas_s3_key("alice", "ds1", "gwas.tsv")
        == "userdata/alice/genetic/ds1/raw/gwas.tsv"
    )


def test_get_gwas_s3_key_prefix_only():
    assert s3.get_gwas_s3_key("alice", "ds1") == "userdata/alice/genetic/ds1/raw"
