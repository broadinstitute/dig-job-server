from pipeline.variant_sifter.loci import chrom_rank, variant_key


def test_chrom_rank_orders_genomically_not_lexically():
    assert chrom_rank("2") < chrom_rank("10")      # not "10" < "2"
    assert chrom_rank("22") < chrom_rank("X") < chrom_rank("Y")
    assert chrom_rank("chr2") == chrom_rank("2")    # tolerate chr-prefix


def test_variant_key_tuple_order():
    row = {"chromosome": "10", "position": 5, "reference": "A", "alt": "G"}
    assert variant_key(row) == (chrom_rank("10"), 5, "A", "G")
