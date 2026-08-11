import pytest

from falcon_prep.ldchunks import (
    CHUNK_SIZE,
    chunk_filename,
    main,
    plan,
    positions_in,
    window_start,
)

HEADER = "rsID\tBETA\tSE\tZ\tCHROM\tPOS\tREF\tALT\tN"


def _sumstats(tmp_path, chrom, positions):
    p = tmp_path / f"{chrom}.sumstats"
    rows = [HEADER]
    for i, pos in enumerate(positions):
        rows.append(f"rs{i}\t0.5\t0.1\t5.0\t{chrom}\t{pos}\tA\tG\t1000.0")
    p.write_text("\n".join(rows) + "\n")
    return p


def test_window_start_floors_to_the_megabase():
    assert window_start(0) == 0
    assert window_start(999_999) == 0
    assert window_start(1_000_000) == 1_000_000
    assert window_start(15_999_828) == 15_000_000


def test_chunk_filename_matches_the_published_naming():
    # Verified against s3://falcon-data-center/ld_chunks/chr21/
    assert chunk_filename(21, 15_000_000) == "chr21_15000000_16000000.ld"
    assert chunk_filename(1, 0) == "chr1_0_1000000.ld"


def test_positions_are_read_from_the_POS_column(tmp_path):
    p = _sumstats(tmp_path, 21, [15_999_828, 10_500_000])
    assert positions_in(str(p)) == [15_999_828, 10_500_000]


def test_variants_in_one_window_need_exactly_one_chunk(tmp_path):
    _sumstats(tmp_path, 21, [15_000_001, 15_500_000, 15_999_999])
    assert plan(str(tmp_path)) == {21: ["chr21_15000000_16000000.ld"]}


def test_variants_straddling_a_boundary_need_both_chunks(tmp_path):
    _sumstats(tmp_path, 21, [15_999_999, 16_000_001])
    assert plan(str(tmp_path)) == {
        21: ["chr21_15000000_16000000.ld", "chr21_16000000_17000000.ld"]
    }


def test_chromosomes_without_a_sumstats_file_are_absent(tmp_path):
    _sumstats(tmp_path, 21, [15_000_000])
    _sumstats(tmp_path, 7, [1_000_000])
    got = plan(str(tmp_path))
    assert sorted(got) == [7, 21]
    assert 13 not in got


def test_non_sumstats_files_are_ignored(tmp_path):
    _sumstats(tmp_path, 21, [15_000_000])
    (tmp_path / "notes.txt").write_text("ignore me\n")
    (tmp_path / "out.wg.genes").write_text("ignore me too\n")
    assert list(plan(str(tmp_path))) == [21]


def test_selection_is_far_smaller_than_the_whole_chromosome(tmp_path):
    # chr21 publishes 38 chunks; a handful of loci must not pull them all.
    _sumstats(tmp_path, 21, [10_500_000, 15_999_828, 30_000_000])
    assert len(plan(str(tmp_path))[21]) == 3


def test_cli_emits_key_and_chromosome_per_chunk(tmp_path, capsys):
    _sumstats(tmp_path, 21, [15_000_000])
    rc = main(["--sumstats-dir", str(tmp_path), "--prefix", "s3://b/ld_chunks"])
    assert rc == 0
    out = capsys.readouterr().out.strip().split("\n")
    assert out == ["s3://b/ld_chunks/chr21/chr21_15000000_16000000.ld\t21"]


def test_cli_exits_3_when_nothing_was_selected(tmp_path):
    assert main(["--sumstats-dir", str(tmp_path)]) == 3


def test_chunk_size_matches_the_published_windows():
    assert CHUNK_SIZE == 1_000_000


def _available(tmp_path, names):
    p = tmp_path / "available.txt"
    p.write_text("\n".join(f"s3://b/ld_chunks/{n}" for n in names) + "\n")
    return str(p)


def test_windows_without_a_published_chunk_are_skipped(tmp_path, capsys):
    # chr20's published windows stop at its 63 Mb end; a variant past that has
    # no chunk, and no LD data either, so FALCON would drop it regardless.
    _sumstats(tmp_path, 20, [30_000_000, 64_500_000])
    avail = _available(tmp_path, ["chr20_30000000_31000000.ld"])
    rc = main(["--sumstats-dir", str(tmp_path), "--prefix", "s3://b/ld_chunks",
               "--available", avail])
    assert rc == 0
    cap = capsys.readouterr()
    assert cap.out.strip() == "s3://b/ld_chunks/chr20/chr20_30000000_31000000.ld\t20"
    assert "1 window(s) have no published chunk" in cap.err


def test_skipping_is_reported_not_silent(tmp_path, capsys):
    _sumstats(tmp_path, 20, [64_500_000])
    avail = _available(tmp_path, ["chr20_30000000_31000000.ld"])
    rc = main(["--sumstats-dir", str(tmp_path), "--available", avail])
    assert rc == 3
    assert "no requested LD chunk exists" in capsys.readouterr().err


def test_without_available_nothing_is_filtered(tmp_path, capsys):
    _sumstats(tmp_path, 20, [64_500_000])
    rc = main(["--sumstats-dir", str(tmp_path), "--prefix", "s3://b/ld_chunks"])
    assert rc == 0
    assert "chr20_64000000_65000000.ld" in capsys.readouterr().out
