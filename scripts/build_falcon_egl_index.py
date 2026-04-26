#!/usr/bin/env python3
"""
Builds frontend/public/data/falcon-egl-index.json from hugeampkpncms.org.

Fetches the catalog (1 request) + 26 per-EGL gene lists (26 requests), builds
an inverted index { GENE_SYMBOL_UPPER: [{page_id, trait, pmid, citation, authors}, ...] },
and writes the result to disk for the FALCON frontend to load as a static asset.

Re-run when you want fresh data. Idempotent. Logs warnings for any EGL whose
CSV cannot be parsed and skips it (the rest of the index still ships).
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
from pathlib import Path

import httpx

CATALOG_URL = "https://hugeampkpncms.org/rest/data?pageid=Gene_page_PEGLs_475"
EGL_URL_TEMPLATE = "https://hugeampkpncms.org/rest/data?pageid={page_id}"

HEADERS = {
    "User-Agent": "FALCON-egl-indexer/1.0 (+https://github.com/broadinstitute/dig-job-server)",
    "Accept": "application/json",
}

# Searched in order; first match wins. `byor_gene` is HuGE AMP's curator-normalized
# canonical column, present across most EGLs even when the paper's own naming differs,
# so it's preferred when available. Paper-specific tail entries handle the few EGLs
# that lack `byor_gene` and use idiosyncratic column names.
GENE_COLUMN_CANDIDATES = (
    "byor_gene",
    "gene",
    "gene symbol",
    "gene_symbol",
    "gene_name",
    "genes",
    "prioritized gene",
    "nominated.gene",
    "locus name",
    "fine mapped gene",
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "frontend" / "public" / "data" / "falcon-egl-index.json"


def fetch_json(client: httpx.Client, url: str) -> object:
    r = client.get(url, headers=HEADERS, timeout=30.0)
    r.raise_for_status()
    return r.json()


def parse_csv_blob(blob: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(blob)))


def find_gene_column(fieldnames: list[str]) -> str | None:
    lowered = {f.lower().strip(): f for f in fieldnames if f}
    for candidate in GENE_COLUMN_CANDIDATES:
        if candidate in lowered:
            return lowered[candidate]
    return fieldnames[0] if fieldnames else None


def main() -> int:
    started = time.time()
    print(f"[build_falcon_egl_index] fetching catalog: {CATALOG_URL}", file=sys.stderr)

    with httpx.Client() as client:
        catalog_payload = fetch_json(client, CATALOG_URL)
        if not isinstance(catalog_payload, list) or not catalog_payload:
            print("[build_falcon_egl_index] catalog: unexpected shape", file=sys.stderr)
            return 1
        catalog_csv = catalog_payload[0].get("field_data_points", "")
        catalog_rows = parse_csv_blob(catalog_csv)
        print(f"[build_falcon_egl_index] catalog has {len(catalog_rows)} EGL studies", file=sys.stderr)

        catalog_meta: dict[str, dict[str, str]] = {}
        for row in catalog_rows:
            page_id = (row.get("Page ID") or "").strip()
            if not page_id:
                continue
            catalog_meta[page_id] = {
                "page_id": page_id,
                "trait": (row.get("Trait") or "N/A").strip(),
                "pmid": (row.get("PMID") or "N/A").strip(),
                "citation": (row.get("Citation") or "N/A").strip(),
                "authors": (row.get("short_name") or "N/A").strip(),
            }

        index: dict[str, list[dict[str, str]]] = {}
        ok = 0
        failed: list[tuple[str, str]] = []
        for page_id, meta in catalog_meta.items():
            url = EGL_URL_TEMPLATE.format(page_id=page_id)
            try:
                payload = fetch_json(client, url)
                if not isinstance(payload, list) or not payload:
                    raise ValueError("unexpected shape")
                blob = payload[0].get("field_data_points", "")
                rows = parse_csv_blob(blob)
                if not rows:
                    raise ValueError("no rows")
                gene_col = find_gene_column(list(rows[0].keys()))
                if not gene_col:
                    raise ValueError("no gene column")
                for row in rows:
                    raw = (row.get(gene_col) or "").strip()
                    if not raw:
                        continue
                    key = raw.upper()
                    index.setdefault(key, []).append(meta)
                ok += 1
                print(f"  [{page_id}] {len(rows)} rows -> indexed by '{gene_col}'", file=sys.stderr)
            except Exception as e:
                print(f"  [{page_id}] FAILED: {e}", file=sys.stderr)
                failed.append((page_id, str(e)))

    output = {
        "generated_at": int(started),
        "source_catalog_url": CATALOG_URL,
        "n_studies_total": len(catalog_meta),
        "n_studies_indexed": ok,
        "n_studies_failed": len(failed),
        "failed_studies": [{"page_id": pid, "error": err} for pid, err in failed],
        "n_genes": len(index),
        "catalog": list(catalog_meta.values()),
        "index": index,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        json.dump(output, f, indent=2, sort_keys=True)
    elapsed = time.time() - started
    print(
        f"[build_falcon_egl_index] wrote {OUT_PATH} "
        f"({ok}/{len(catalog_meta)} studies, {len(index)} genes, {elapsed:.1f}s)",
        file=sys.stderr,
    )
    return 0 if ok > 0 else 2


if __name__ == "__main__":
    sys.exit(main())
