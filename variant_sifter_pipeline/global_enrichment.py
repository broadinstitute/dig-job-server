"""Build the per-dataset global-enrichment records from S-LDSC tissue results."""
import json
import math
from typing import Iterable, Optional

from variant_sifter_pipeline.index_build import global_enrichment_key


def build_global_enrichment(lines: Iterable[str], guid: str,
                            ancestry: Optional[str]) -> list:
    """Parse headerless tissue.output.tsv lines (annotation, tissue, biosample,
    enrichment, pValue). Malformed, blank or non-finite rows are skipped."""
    records = []
    for line in lines:
        fields = line.rstrip("\r\n").split("\t")
        if len(fields) != 5:
            continue
        annotation, tissue, biosample, enrichment, p_value = fields
        try:
            snps = float(enrichment)
            p = float(p_value)
        except ValueError:
            continue
        if not (math.isfinite(snps) and math.isfinite(p)):
            continue
        records.append({
            "phenotype": guid,
            "ancestry": ancestry,
            "annotation": annotation,
            "tissue": tissue,
            "biosample": biosample,
            "SNPs": snps,
            "expectedSNPs": 1,
            "pValue": p,
        })
    return records


def write_global_enrichment(s3, bucket: str, records: list, guid: str) -> None:
    """Write records as JSON lines; an empty list writes an empty object so the
    index still builds."""
    body = "".join(json.dumps(r) + "\n" for r in records)
    s3.put_object(Bucket=bucket, Key=global_enrichment_key(guid), Body=body.encode())
