from pipeline.variant_sifter.canonicalize import canonicalize


def test_canonicalize_renames_via_col_map():
    col_map = {"chromosome": "CHR", "position": "BP", "reference": "A2",
               "alt": "A1", "pValue": "P", "beta": "BETA", "se": "SE",
               "rsid": "SNP"}
    upload_row = {"CHR": "8", "BP": "200", "A2": "C", "A1": "T",
                  "P": 1e-9, "BETA": -0.3, "SE": 0.04, "SNP": "rs2", "EXTRA": "x"}
    out = canonicalize(upload_row, col_map)
    assert out == {"chromosome": "8", "position": "200", "reference": "C",
                   "alt": "T", "pValue": 1e-9, "beta": -0.3, "se": 0.04,
                   "rsid": "rs2"}   # only mapped fields; EXTRA dropped


def test_canonicalize_skips_unmapped_or_absent():
    # col_map references a column not in the row → that field is omitted.
    out = canonicalize({"CHR": "1"}, {"chromosome": "CHR", "pValue": "P"})
    assert out == {"chromosome": "1"}
