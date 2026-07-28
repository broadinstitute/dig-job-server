"""Allele orientation against the reference genome.

The rules encoded here are invisible from the code that depends on them: a
mis-oriented variant id fails downstream with an empty-but-successful response,
and a sign error in beta is not detectable at all without a reference.
"""

import textwrap

import pytest

from variant_sifter_pipeline import reference as ref_mod
from variant_sifter_pipeline.reference import (
    ALREADY_CANONICAL,
    FLIPPED,
    INDEL_SKIPPED,
    NEITHER_MATCHES,
    NO_REFERENCE_BASE,
    ReferenceGenome,
    base_offset,
    normalize_contig,
    orient_record,
    orient_records,
    parse_fai,
)

# Real chr22 line from the b37 .fai: 80 bases per line, 81 bytes with the newline.
REAL_FAI_LINE = "22\t51304566\t2865101503\t80\t81"


@pytest.fixture
def genome(tmp_path):
    """A two-contig FASTA wrapped at 6 bases/line, with a hand-written .fai."""
    seq1 = "ACGTAC" "GGTTAA" "CC"          # contig "1", 14 bases
    seq2 = "TTTTTT" "GA"                    # contig "MT", 8 bases
    fasta = tmp_path / "ref.fasta"
    body = f">1\n{textwrap.fill(seq1, 6)}\n>MT\n{textwrap.fill(seq2, 6)}\n"
    fasta.write_text(body)
    off1 = body.index(seq1[:6])
    off2 = body.index(seq2[:6])
    (tmp_path / "ref.fasta.fai").write_text(
        f"1\t{len(seq1)}\t{off1}\t6\t7\nMT\t{len(seq2)}\t{off2}\t6\t7\n"
    )
    with ReferenceGenome(str(fasta)) as g:
        yield g


def test_parse_fai_reads_the_five_columns_offsets_need():
    assert parse_fai(REAL_FAI_LINE) == {"22": (51304566, 2865101503, 80, 81)}


def test_base_offset_accounts_for_line_wrapping():
    """linewidth exceeds linebases by the newline; ignoring that drifts by one
    byte per line, which silently returns a neighbouring base."""
    meta = (51304566, 2865101503, 80, 81)
    assert base_offset(meta, 1) == 2865101503          # first base, no newlines yet
    assert base_offset(meta, 80) == 2865101503 + 79    # last base of line 1
    assert base_offset(meta, 81) == 2865101503 + 81    # line 2 starts after \n


def test_normalize_contig_matches_b37_naming():
    assert normalize_contig("chr22") == "22"
    assert normalize_contig("CHR22") == "22"
    assert normalize_contig("22") == "22"
    assert normalize_contig("M") == "MT"


def test_base_at_reads_across_wrapped_lines(genome):
    # seq "ACGTACGGTTAACC": position 7 is the first base of line 2.
    assert genome.base_at("1", 1) == "A"
    assert genome.base_at("1", 6) == "C"
    assert genome.base_at("1", 7) == "G"
    assert genome.base_at("1", 14) == "C"


def test_base_at_returns_none_off_the_end_or_off_contig(genome):
    assert genome.base_at("1", 15) is None
    assert genome.base_at("1", 0) is None
    assert genome.base_at("99", 1) is None


def test_already_canonical_records_are_untouched(genome):
    rec = {"chromosome": "1", "position": 1, "reference": "A", "alt": "G",
           "beta": 0.5, "zScore": 2.0}
    out, outcome = orient_record(rec, genome)
    assert outcome == ALREADY_CANONICAL
    assert out == rec


def test_flipping_swaps_alleles_and_negates_effect_direction(genome):
    """beta is the effect per copy of ALT. Swapping alleles without negating it
    would invert every reported effect direction -- worse than the missing-LD
    symptom this exists to fix."""
    rec = {"chromosome": "1", "position": 1, "reference": "G", "alt": "A",
           "beta": 0.5, "zScore": 2.0, "stdErr": 0.25, "pValue": 1e-8}
    out, outcome = orient_record(rec, genome)
    assert outcome == FLIPPED
    assert (out["reference"], out["alt"]) == ("A", "G")
    assert out["beta"] == -0.5
    assert out["zScore"] == -2.0
    # Direction-free quantities must NOT change.
    assert out["stdErr"] == 0.25
    assert out["pValue"] == 1e-8


def test_orient_record_never_mutates_its_input(genome):
    rec = {"chromosome": "1", "position": 1, "reference": "G", "alt": "A", "beta": 0.5}
    orient_record(rec, genome)
    assert rec == {"chromosome": "1", "position": 1, "reference": "G",
                   "alt": "A", "beta": 0.5}


def test_flip_handles_records_with_no_effect_fields(genome):
    rec = {"chromosome": "1", "position": 1, "reference": "G", "alt": "A"}
    out, outcome = orient_record(rec, genome)
    assert outcome == FLIPPED
    assert (out["reference"], out["alt"]) == ("A", "G")


def test_indels_are_left_alone_and_counted(genome):
    """Correct indel handling needs left-alignment and a multi-base ref span.
    They must be reported, not silently passed through as if oriented."""
    rec = {"chromosome": "1", "position": 1, "reference": "AC", "alt": "A"}
    out, outcome = orient_record(rec, genome)
    assert outcome == INDEL_SKIPPED
    assert out == rec


def test_neither_allele_matching_is_reported_not_guessed(genome):
    """Opposite strand or wrong genome build. Guessing an orientation here would
    fabricate data; a dataset full of these needs to be visible."""
    rec = {"chromosome": "1", "position": 1, "reference": "C", "alt": "T"}
    out, outcome = orient_record(rec, genome)
    assert outcome == NEITHER_MATCHES
    assert out == rec


def test_unaddressable_locus_is_reported(genome):
    rec = {"chromosome": "99", "position": 1, "reference": "A", "alt": "G"}
    _, outcome = orient_record(rec, genome)
    assert outcome == NO_REFERENCE_BASE


def test_orient_records_resorts_because_flipping_changes_the_sort_key(genome):
    """loci.variant_key includes the alleles, so a flip can reorder two variants
    at one position. bioindex requires locus-ordered input."""
    records = [
        {"chromosome": "1", "position": 1, "reference": "G", "alt": "A"},  # -> A/G
        {"chromosome": "1", "position": 1, "reference": "A", "alt": "C"},  # canonical
    ]
    out, counts = orient_records(records, genome)
    assert counts == {FLIPPED: 1, ALREADY_CANONICAL: 1}
    assert [(r["reference"], r["alt"]) for r in out] == [("A", "C"), ("A", "G")]


def test_ensure_local_reference_honours_the_override(monkeypatch):
    """The override keeps tests and any future shared mount off the network."""
    monkeypatch.setenv("VS_REFERENCE_FASTA", "/somewhere/ref.fasta")
    assert ref_mod.ensure_local_reference() == "/somewhere/ref.fasta"
