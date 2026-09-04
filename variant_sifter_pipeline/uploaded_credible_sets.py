"""User-uploaded credible sets -> the portal's credible-set records.

The pure part mirrors dig-aggregator-methods' convert_credible_set
(credible-sets/credibleSets.py): drop non-positive posterior probabilities,
dedupe, renormalise per set, derive varId / clump bounds / lead SNP /
alignment. Set ids are namespaced by the upload's slug so two uploads can both
contain a set called "1", and `source` names the upload so the sifter can tell
uploaded sets from the derived `sifter-abf` ones.

The S3 sync lives in the same module (below) so the object layout has one owner.
"""

import csv
import gzip
import io
import json
import math

from .canonicalize import canonicalize
from .index_build import (credible_sets_prefix, credible_variants_prefix,
                          upload_sets_key, upload_slug_of_key, upload_variants_key)
from .loci import chrom_rank
from .reference import normalize_contig, orient_records


def _to_float(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def sort_variant_rows(rows):
    """Index schema `phenotype,credibleSetId` groups by key; position within."""
    return sorted(rows, key=lambda r: (r["credibleSetId"], r["position"]))


def sort_set_rows(rows):
    """Index schema `phenotype,chromosome:start-end` wants locus order."""
    return sorted(rows, key=lambda r: (chrom_rank(r["chromosome"]), r["start"]))


def refresh_var_ids(rows):
    """Recompute varId from the alleles (orientation may have swapped them)."""
    for r in rows:
        r["varId"] = f'{r["chromosome"]}:{r["position"]}:{r["reference"]}:{r["alt"]}'
    return rows


def add_alignment(rows):
    """alignment = sign(beta * lead beta) per set, only where both exist.
    Must run AFTER orientation, which negates beta on flipped variants."""
    lead_beta = {r["credibleSetId"]: r.get("beta") for r in rows if r.get("leadSNP")}
    for r in rows:
        lb, b = lead_beta.get(r["credibleSetId"]), r.get("beta")
        if lb is not None and b is not None:
            product = b * lb
            r["alignment"] = float((product > 0) - (product < 0))
    return rows


def build_uploaded_credible_sets(rows, guid: str, dataset: str, *, slug: str, name: str,
                                 ancestry: "str | None" = None):
    """(variant_rows, set_rows) for one upload's canonicalised rows."""
    by_set: "dict[str, list[dict]]" = {}
    seen = set()
    for r in rows:
        pp = _to_float(r.get("posteriorProbability"))
        if pp is None or pp <= 0:
            continue
        chrom = normalize_contig(r["chromosome"])
        pos = int(str(r["position"]).strip())
        ref, alt = str(r["reference"]).upper(), str(r["alt"]).upper()
        raw_id = str(r["credibleSetId"]).strip()
        var_id = f"{chrom}:{pos}:{ref}:{alt}"
        if (raw_id, var_id) in seen:
            continue
        seen.add((raw_id, var_id))
        rec = {
            "phenotype": guid,
            "credibleSetId": f"{slug}:{raw_id}",
            "dataset": dataset,
            "varId": var_id,
            "chromosome": chrom,
            "position": pos,
            "reference": ref,
            "alt": alt,
            "posteriorProbability": pp,
            "source": f"upload:{slug}",
        }
        if ancestry:
            rec["ancestry"] = ancestry
        for src, dst in (("pValue", "pValue"), ("beta", "beta"), ("se", "stdErr"), ("n", "n")):
            value = _to_float(r.get(src))
            if value is not None:
                rec[dst] = value
        if r.get("rsid"):
            rec["dbSNP"] = str(r["rsid"])
        by_set.setdefault(raw_id, []).append(rec)

    variant_rows, set_rows = [], []
    for raw_id, members in by_set.items():
        members.sort(key=lambda m: m["position"])
        total = sum(m["posteriorProbability"] for m in members)
        for m in members:
            m["posteriorProbability"] = m["posteriorProbability"] / total
        start, end = members[0]["position"], members[-1]["position"] + 1
        lead = max(members, key=lambda m: (m["posteriorProbability"], -m["position"]))
        for m in members:
            m["leadSNP"] = m is lead
            m["clumpStart"], m["clumpEnd"] = start, end
        variant_rows.extend(members)
        set_row = {
            "phenotype": guid,
            "credibleSetId": f"{slug}:{raw_id}",
            "dataset": dataset,
            "chromosome": members[0]["chromosome"],
            "start": start,
            "end": end,
            "source": f"upload:{slug}",
            "uploadName": name,
        }
        if ancestry:
            set_row["ancestry"] = ancestry
        set_rows.append(set_row)
    return sort_variant_rows(variant_rows), sort_set_rows(set_rows)


# ---- S3: read uploads, write objects, reconcile ------------------------------


def uploads_prefix(username: str, dataset: str) -> str:
    """Mirror of job_server.s3.get_credible_set_s3_prefix's parent folder."""
    return f"userdata/{username}/genetic/{dataset}/credible_sets/"


def _list_keys(s3, bucket: str, prefix: str):
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            yield obj["Key"]


def list_upload_metadata(s3, bucket: str, username: str, dataset: str) -> "list[dict]":
    """Every attached upload's metadata (job_server.model.CredibleSetInfo as a
    dict), sorted by slug for stable logs."""
    metas = []
    for key in _list_keys(s3, bucket, uploads_prefix(username, dataset)):
        if key.endswith("/raw/metadata"):
            body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            metas.append(json.loads(body))
    return sorted(metas, key=lambda m: m["slug"])


def read_upload_rows(s3, bucket: str, username: str, dataset: str, meta: dict):
    """Raw rows (upload column names) of one credible-set file. Files are small
    (the API caps them at 20 MB) so this reads the object whole; gzip is
    detected by magic bytes, as the validator does, not by file name."""
    key = f'{uploads_prefix(username, dataset)}{meta["slug"]}/raw/{meta["file"]}'
    raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    yield from csv.DictReader(io.StringIO(raw.decode("utf-8")), delimiter=meta.get("separator") or "\t")


def existing_upload_keys(s3, bucket: str, guid: str) -> "dict[str, list[str]]":
    """{slug: [object keys]} for every upload object currently under the
    dataset's two credible-set prefixes."""
    found: "dict[str, list[str]]" = {}
    for prefix in (credible_sets_prefix(guid), credible_variants_prefix(guid)):
        for key in _list_keys(s3, bucket, prefix):
            slug = upload_slug_of_key(key)
            if slug:
                found.setdefault(slug, []).append(key)
    return found


def sync_uploaded_credible_sets(s3, upload_bucket: str, bioindex_bucket: str, username: str,
                                dataset: str, guid: str, *, ancestry: "str | None" = None,
                                genome=None) -> dict:
    """Write `upload-<slug>.json` objects for every attached upload and delete
    the objects of uploads that were detached. Does NOT index: the caller
    rebuilds the two credible-set indexes once after all writers have run.

    Any exception propagates: an upload the API accepted but the pipeline
    cannot read is a bug that must fail the job, not vanish silently.
    """
    counts: dict = {}
    metas = list_upload_metadata(s3, upload_bucket, username, dataset)
    for meta in metas:
        rows = (canonicalize(r, meta["col_map"]) for r in read_upload_rows(s3, upload_bucket, username, dataset, meta))
        variants, sets_ = build_uploaded_credible_sets(
            rows, guid, dataset, slug=meta["slug"], name=meta["name"], ancestry=ancestry)
        if genome is not None:
            variants, _ = orient_records(variants, genome)   # re-sorts by locus
            variants = sort_variant_rows(refresh_var_ids(variants))
        add_alignment(variants)
        for key, out_rows in ((upload_variants_key(guid, meta["slug"]), variants),
                              (upload_sets_key(guid, meta["slug"]), sets_)):
            body = "".join(json.dumps(r) + "\n" for r in out_rows)
            s3.put_object(Bucket=bioindex_bucket, Key=key, Body=body.encode())
        counts[meta["slug"]] = {"variants": len(variants), "sets": len(sets_)}

    live = {m["slug"] for m in metas}
    for slug, keys in existing_upload_keys(s3, bioindex_bucket, guid).items():
        if slug not in live:
            for key in keys:
                s3.delete_object(Bucket=bioindex_bucket, Key=key)
            counts[slug] = "removed"
    return counts
