"""Derive credible sets from a sifted GWAS: the portal's bottom-line recipe
(PLINK LD-clumping + ABF posterior probabilities), ported from
dig-aggregator-methods without its Spark/numpy dependencies.
"""

import json
import math
import os
import stat
import subprocess
import tempfile
import zipfile
from statistics import NormalDist

from .index_build import (credible_sets_key, credible_variants_key,
                          index_credible_sets, index_credible_variants)
from .loci import chrom_rank

# Where the aggregator keeps the clumping assets this port reuses: PLINK 1.9,
# the per-ancestry 1000G bfiles, and the varId->rsID dbSNP-common map (see
# bottom-line/install-plink.sh). The Batch job role needs read access here.
CLUMPING_BUCKET = os.getenv("VS_CLUMPING_BUCKET", "dig-analysis-bin")
# Downloaded assets are cached under this directory for the container's life.
CLUMPING_DIR = os.getenv("VS_CLUMPING_DIR",
                         os.path.join(tempfile.gettempdir(), "vs-clumping"))
_PLINK_ZIP_KEY = "plink/plink_linux_x86_64_20201019.zip"
_DBSNP_KEY = "snps/dbSNP_common_GRCh37.csv"

# Ancestry -> 1000G super-population panel: the portal codes from runPlink.py's
# map, plus the 1000G-style codes (EUR/AMR/...) that upload metadata actually
# stores. Absent/Mixed/unknown uses EU like the portal's trans-ethnic bottom line.
_G1000_BY_ANCESTRY = {
    "AA": "afr", "AF": "afr", "SSAF": "afr", "EU": "eur", "HS": "amr",
    "EA": "eas", "SA": "sas", "GME": "sas", "Mixed": "eur", "TE": "eur",
    "AFR": "afr", "EUR": "eur", "AMR": "amr", "EAS": "eas", "SAS": "sas",
}


def g1000_panel(ancestry: "str | None") -> str:
    return _G1000_BY_ANCESTRY.get(ancestry or "Mixed", "eur")

# The portal's clumping thresholds (bottom-line runPlink.py `analysis` params):
# clumps seed at genome-wide significance and admit members down to P2.
P1 = 5e-8
P2 = 5e-6

# ABF implicit-prior parameter (see credible-sets/credibleSets.py in the
# aggregator): chosen so p=5e-8 lands near posterior probability 0.75.
_K = 0.974
# norm.ppf overflows to infinity below this; the aggregator clamps identically.
_MIN_P = 1e-323

_NORMAL = NormalDist()


def _p_to_z(p_value: float) -> float:
    return abs(_NORMAL.inv_cdf(max(p_value, _MIN_P) / 2.0))


def bayes_pp(pvalues: "list[float]") -> "list[float]":
    """Normalized approximate-Bayes-factor posterior probabilities for the
    variants of one clump, from their p-values alone."""
    abfs = []
    for p in pvalues:
        z = _p_to_z(p)
        abfs.append(1 / (1 + _K) ** 0.5 * math.exp(z * z * _K / 2 / (1 + _K)))
    total = sum(abfs)
    return [a / total for a in abfs]


def _parse_sp2(sp2: str) -> "list[str]":
    """SP2 is `NONE` or a comma list of rsID(file-number) entries."""
    if sp2 == "NONE":
        return []
    return [s.split("(", 1)[0] for s in sp2.split(",")]


def clump_groups(clumped_text: str) -> "list[set[str]]":
    """Groups of rsIDs from a plink `.clumped` report: each index SNP plus its
    SP2 members, with groups that share a member merged (the connected-
    components step of runPlink.py, as union-find)."""
    parent: "dict[str, str]" = {}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        parent.setdefault(a, a)
        parent.setdefault(b, b)
        parent[find(a)] = find(b)

    lines = clumped_text.splitlines()
    for line in lines[1:]:  # skip the header
        fields = line.split()
        if not fields:
            continue
        snp, sp2 = fields[2], fields[11]
        parent.setdefault(snp, snp)
        for member in _parse_sp2(sp2):
            union(snp, member)

    groups: "dict[str, set[str]]" = {}
    for snp in parent:
        groups.setdefault(find(snp), set()).add(snp)
    return list(groups.values())


def _var_id(rec: dict) -> str:
    return f'{rec["chromosome"]}:{rec["position"]}:{rec["reference"]}:{rec["alt"]}'


def _sign(x: float) -> float:
    return float((x > 0) - (x < 0))


def derive_credible_sets(records, guid: str, dataset: str, *,
                         run_plink, ancestry: "str | None" = None,
                         rsid_lookup=None):
    """Derive credible sets from a dataset's association records.

    `run_plink` takes the rsID-bearing candidate records and returns the text
    of plink's `.clumped` report (or None when plink produced no clumps);
    `rsid_lookup` optionally maps varIds without an upload rsID to one (the
    dbSNP-common fallback). Returns (variant_rows, set_rows) shaped like the
    main portal's credible-variants / credible-sets records.
    """
    candidates = [dict(r) for r in records
                  if r.get("pValue") is not None and r["pValue"] <= P2]
    if not any(r["pValue"] <= P1 for r in candidates):
        return [], []

    missing = {_var_id(r) for r in candidates if not r.get("dbSNP")}
    if missing and rsid_lookup is not None:
        found = rsid_lookup(missing)
        for r in candidates:
            if not r.get("dbSNP"):
                rsid = found.get(_var_id(r))
                if rsid:
                    r["dbSNP"] = rsid

    common = [r for r in candidates if r.get("dbSNP")]
    # rsID-less variants can't be LD-clumped; keep the genome-wide-significant
    # ones as singleton sets (clumpedAssociations.py's 'rare' path).
    rare = [r for r in candidates if not r.get("dbSNP") and r["pValue"] <= P1]

    clumps: "list[list[dict]]" = []
    if common:
        clumped_text = run_plink(common)
        if clumped_text:
            by_rsid = {r["dbSNP"]: r for r in common}
            for group in clump_groups(clumped_text):
                members = [by_rsid[rs] for rs in group if rs in by_rsid]
                if members:
                    clumps.append(members)
    clumps.extend([r] for r in rare)
    clumps.sort(key=lambda ms: (chrom_rank(ms[0]["chromosome"]),
                                min(r["position"] for r in ms)))

    variant_rows: "list[dict]" = []
    set_rows: "list[dict]" = []
    for i, members in enumerate(clumps, start=1):
        set_id = f"{i}_sifter"
        members.sort(key=lambda r: r["position"])
        start = members[0]["position"]
        end = max(r["position"] for r in members) + 1
        pps = bayes_pp([r["pValue"] for r in members])
        lead = min(members, key=lambda r: r["pValue"])
        lead_beta = lead.get("beta")

        for rec, pp in zip(members, pps):
            row = {
                "phenotype": guid,
                "credibleSetId": set_id,
                "dataset": dataset,
                "varId": _var_id(rec),
                "chromosome": rec["chromosome"],
                "position": rec["position"],
                "reference": rec["reference"],
                "alt": rec["alt"],
                "pValue": rec["pValue"],
                "posteriorProbability": pp,
                "leadSNP": rec is lead,
                "clumpStart": start,
                "clumpEnd": end,
                "source": "sifter-abf",
            }
            if ancestry:
                row["ancestry"] = ancestry
            for k in ("beta", "stdErr", "n", "dbSNP"):
                if rec.get(k) is not None:
                    row[k] = rec[k]
            if lead_beta is not None and rec.get("beta") is not None:
                row["alignment"] = _sign(rec["beta"] * lead_beta)
            variant_rows.append(row)

        set_row = {
            "phenotype": guid,
            "credibleSetId": set_id,
            "dataset": dataset,
            "chromosome": members[0]["chromosome"],
            "start": start,
            "end": end,
        }
        if ancestry:
            set_row["ancestry"] = ancestry
        set_rows.append(set_row)

    return variant_rows, set_rows


# --- production plink runner + dbSNP fallback -----------------------------


def _ensure_download(s3, key: str, dest: str) -> str:
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = f"{dest}.partial"
        s3.download_file(CLUMPING_BUCKET, key, tmp)
        os.rename(tmp, dest)
    return dest


def _ensure_plink(s3) -> str:
    """The static PLINK 1.9 binary, downloaded and unzipped once."""
    plink = os.getenv("VS_PLINK_BIN") or os.path.join(CLUMPING_DIR, "plink")
    if not os.path.exists(plink):
        zip_path = _ensure_download(s3, _PLINK_ZIP_KEY,
                                    os.path.join(CLUMPING_DIR, "plink.zip"))
        with zipfile.ZipFile(zip_path) as zf:
            zf.extract("plink", CLUMPING_DIR)
        os.chmod(plink, os.stat(plink).st_mode | stat.S_IXUSR | stat.S_IXGRP)
    return plink


def _ensure_panel(s3, g1000: str) -> str:
    """The ancestry's 1000G bfile set; returns the --bfile prefix path."""
    name = f"g1000_{g1000}"
    panel_dir = os.path.join(CLUMPING_DIR, name)
    if not os.path.isdir(panel_dir):
        zip_path = _ensure_download(s3, f"clumping/{name}.zip",
                                    os.path.join(CLUMPING_DIR, f"{name}.zip"))
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(panel_dir)
        os.remove(zip_path)
    return os.path.join(panel_dir, name)


def make_plink_runner(ancestry: "str | None"):
    """A run_plink callable for derive_credible_sets: fetches PLINK + the
    ancestry's LD panel on first use, clumps with the portal's thresholds,
    and returns the `.clumped` report text (None when nothing clumped)."""
    import boto3  # deferred so pure-logic callers never need it

    g1000 = g1000_panel(ancestry)

    def run(assoc_rows) -> "str | None":
        s3 = boto3.client("s3")
        plink = _ensure_plink(s3)
        bfile = _ensure_panel(s3, g1000)

        workdir = tempfile.mkdtemp(prefix="clump-", dir=CLUMPING_DIR)
        assoc_path = os.path.join(workdir, "snps.assoc")
        with open(assoc_path, "w") as f:
            f.write("CHR\tSNP\tBP\tP\n")
            for r in assoc_rows:
                f.write(f'{r["chromosome"]}\t{r["dbSNP"]}\t'
                        f'{r["position"]}\t{r["pValue"]}\n')

        out_prefix = os.path.join(workdir, "plink")
        # Like runPlink.py, the exit code is ignored: plink exits non-zero for
        # benign reasons (e.g. no clumpable SNPs); presence of the report file
        # is the signal.
        subprocess.run([
            plink, "--bfile", bfile,
            "--clump-p1", str(P1), "--clump-p2", str(P2),
            "--clump-r2", "0.01", "--clump-kb", "5000",
            "--clump", assoc_path, "--out", out_prefix,
        ], check=False)

        clumped = f"{out_prefix}.clumped"
        if not os.path.isfile(clumped):
            return None
        with open(clumped) as f:
            return f.read()

    return run


def dbsnp_rsid_lookup(varids: "set[str]") -> "dict[str, str]":
    """varId -> rsID from the aggregator's dbSNP-common map, for uploads that
    carry no rsid column. Streamed and filtered; on any failure (asset or
    access missing) returns {} so derivation degrades to the singleton path
    rather than dying."""
    import boto3

    try:
        s3 = boto3.client("s3")
        body = s3.get_object(Bucket=CLUMPING_BUCKET, Key=_DBSNP_KEY)["Body"]
        found: "dict[str, str]" = {}
        header = None
        for raw in body.iter_lines():
            fields = raw.decode().rstrip("\n").split("\t")
            if header is None:
                header = {col: i for i, col in enumerate(fields)}
                continue
            var_id = fields[header["varId"]]
            if var_id in varids:
                found[var_id] = fields[header["dbSNP"]]
                if len(found) == len(varids):
                    break
        return found
    except Exception as exc:
        print(f"WARNING: dbSNP rsID lookup unavailable ({exc}); "
              f"clumping only upload-supplied rsIDs")
        return {}


def build_and_index_credible_sets(s3, bucket: str, records, guid: str, *,
                                  dataset: str,
                                  ancestry: "str | None" = None) -> int:
    """Derive, write, and index this dataset's credible sets. Both objects are
    written (and both indexes built) even when empty, so frontend queries get
    clean empty results instead of a missing index. Returns the number of
    credible-set variant rows."""
    variants, sets_ = derive_credible_sets(
        records, guid, dataset, ancestry=ancestry,
        run_plink=make_plink_runner(ancestry),
        rsid_lookup=dbsnp_rsid_lookup)

    for key, rows in ((credible_variants_key(guid), variants),
                      (credible_sets_key(guid), sets_)):
        body = "".join(json.dumps(r) + "\n" for r in rows)
        s3.put_object(Bucket=bucket, Key=key, Body=body.encode())

    index_credible_variants(guid)
    index_credible_sets(guid)
    return len(variants)
