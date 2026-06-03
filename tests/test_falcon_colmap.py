from job_server.falcon import col_map_to_sumstats_columns


def test_maps_known_keys_and_marks_z_none():
    cm = {
        "chromosome": "CHR", "position": "BP", "rsid": "ID", "beta": "BETA",
        "se": "SE", "reference": "OA", "alt": "EA", "n": "N",
    }
    assert col_map_to_sumstats_columns(cm) == {
        "sumstats-chr-col": "CHR",
        "sumstats-pos-col": "BP",
        "sumstats-id-col": "ID",
        "sumstats-beta-col": "BETA",
        "sumstats-se-col": "SE",
        "sumstats-ref-col": "OA",
        "sumstats-alt-col": "EA",
        "sumstats-n-col": "N",
        "sumstats-z-col": "None",
    }


def test_omits_missing_keys_and_ignores_unmapped():
    out = col_map_to_sumstats_columns({"chromosome": "CHR", "pValue": "P", "oddsRatio": "OR"})
    assert out["sumstats-chr-col"] == "CHR"
    assert out["sumstats-z-col"] == "None"
    assert "sumstats-id-col" not in out
    assert "sumstats-freq-col" not in out
    assert set(out) == {"sumstats-chr-col", "sumstats-z-col"}


def test_empty_col_map_still_marks_z_none():
    assert col_map_to_sumstats_columns({}) == {"sumstats-z-col": "None"}
