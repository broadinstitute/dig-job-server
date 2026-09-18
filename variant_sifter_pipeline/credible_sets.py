"""Derive credible sets from a sifted GWAS.

A port of the aggregator's `finemapping` package (dig-aggregator-methods,
branch `finemap`, deployed to s3://dig-analysis-bin/cojo/finemapping/), which
is itself the Open Targets Genetics fine-mapping method (Ed Mountjoy):

  1. per chromosome, GCTA-COJO stepwise selection on the genome-wide-
     significant variants gives the conditionally independent index variants;
  2. each index variant is conditioned on the other index variants within a
     2 Mb window (GCTA `--cojo-cond`);
  3. a Wakefield approximate-Bayes-factor 95% / 99% credible set is built from
     the conditional statistics within 500 kb of the index variant.

One credible set per index variant. Written without the reference's pandas /
dask / scipy dependencies: the bioindex runtime this container shares pins
old libraries, so everything here is stdlib + the GCTA binary. Plan:
docs/superpowers/plans/2026-09-17-derived-credible-sets-cojo.md.
"""

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from statistics import NormalDist

from .index_build import credible_sets_key, credible_variants_key
from .loci import chrom_rank

# Where the aggregator keeps the assets this port reuses: the per-chromosome
# LD panel (cojo/bfiles/) and the varId->rsID dbSNP-common map. The Batch job
# role has read access to this bucket (ClumpingAssetsBucket in the stack).
CLUMPING_BUCKET = os.getenv("VS_CLUMPING_BUCKET", "dig-analysis-bin")
# Downloaded assets and GCTA scratch files live under this directory.
CLUMPING_DIR = os.getenv("VS_CLUMPING_DIR",
                         os.path.join(tempfile.gettempdir(), "vs-clumping"))
# GCTA 1.95.2 is installed in the pipeline image (variant_sifter_pipeline/Dockerfile).
GCTA_BIN = os.getenv("VS_GCTA_BIN", "/opt/gcta/gcta")
# The aggregator's LD reference: one PLINK bfile set per chromosome, rsID-keyed
# .bim. Despite the name it holds all 2504 1000G phase-3 samples, and it is the
# only panel the aggregator's finemapping runs with, so every ancestry uses it.
PANEL_PREFIX = "cojo/bfiles/1000G.EUR.QC"
_DBSNP_KEY = "snps/dbSNP_common_GRCh37.csv"

# Analysis parameters: the aggregator's only_cojo.config.yaml, verbatim.
GWS_P = 5e-8            # cojo_p / gwas_pval_threshold
MIN_MAF = 0.01          # min_maf
COJO_WINDOW_KB = 2000   # cojo_wind
COJO_COLLINEAR = 0.9    # cojo_colin
FM_WINDOW_KB = 500      # fm_wind
PP_THRESHOLD = 0.001    # pp_threshold
PRIOR_SD = 0.15         # Wakefield prior sd for a quantitative trait
# exclude_MHC: the reference's b37/b38 coordinates on chromosome 6.
MHC = {"GRCh37": (28477797, 33448354), "GRCh38": (28510120, 33480577)}

METHOD = "COJO+ABF"
SOURCE = "sifter-cojo"

# norm.ppf overflows to infinity below this; the aggregator clamps identically.
# Also the value an uploaded pValue of 0 is stored as (uploaded_credible_sets),
# mirrored by job_server.credible_sets.MIN_P_VALUE.
MIN_P = 1e-323

_NORMAL = NormalDist()


def _p_to_z(p_value: float) -> float:
    return abs(_NORMAL.inv_cdf(max(p_value, MIN_P) / 2.0))


def _var_id(rec: dict) -> str:
    return f'{rec["chromosome"]}:{rec["position"]}:{rec["reference"]}:{rec["alt"]}'


def _sign(x: float) -> float:
    return float((x > 0) - (x < 0))


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# --- step 0: the sumstats the method works on -------------------------------


def mhc_bounds(genome_build: "str | None") -> "tuple[int, int]":
    return MHC["GRCh38" if genome_build and "38" in str(genome_build) else "GRCh37"]


def prepare_sumstats(records, genome_build: "str | None" = None) -> "list[dict]":
    """The reference's load_sumstats: keep variants that carry everything the
    method needs (rsID for the LD panel, beta/stdErr for GCTA, eaf and n for
    the ABF variance), drop MAF < MIN_MAF and the MHC. Returns copies with the
    numeric fields coerced to float, in the input order."""
    mhc_lo, mhc_hi = mhc_bounds(genome_build)
    out: "list[dict]" = []
    for rec in records:
        p, beta, se = _float(rec.get("pValue")), _float(rec.get("beta")), _float(rec.get("stdErr"))
        eaf, n = _float(rec.get("eaf")), _float(rec.get("n"))
        if not rec.get("dbSNP") or None in (p, beta, se, eaf, n):
            continue
        if min(eaf, 1.0 - eaf) < MIN_MAF:
            continue
        if str(rec["chromosome"]) == "6" and mhc_lo <= int(rec["position"]) <= mhc_hi:
            continue
        row = dict(rec)
        row.update(pValue=p, beta=beta, stdErr=se, eaf=eaf, n=n,
                   position=int(rec["position"]), chromosome=str(rec["chromosome"]))
        out.append(row)
    return out


# --- GCTA file formats -------------------------------------------------------


def ma_lines(rows) -> "list[str]":
    """GCTA `--cojo-file` rows: SNP A1 A2 freq b se p N, A1 being the effect
    allele (alt) like the reference's sumstat_to_gcta. p is never written as 0
    (GCTA rejects it)."""
    lines = ["SNP\tA1\tA2\tfreq\tb\tse\tp\tN"]
    for r in rows:
        lines.append("\t".join([
            r["dbSNP"], r["alt"], r["reference"], repr(r["eaf"]), repr(r["beta"]),
            repr(r["stdErr"]), repr(max(r["pValue"], MIN_P)), repr(r["n"])]))
    return lines


def parse_cojo_table(text: "str | None") -> "list[dict]":
    """A `.jma.cojo` / `.cma.cojo` report (tab-separated, header row) as dicts;
    `SNP` stays a string, every other field becomes a float or None (GCTA
    writes `NA`, e.g. for the SNPs a `--cojo-cond` run conditioned on)."""
    if not text:
        return []
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return []
    header = lines[0].split("\t")
    rows = []
    for ln in lines[1:]:
        fields = ln.split("\t")
        row = {}
        for k, v in zip(header, fields):
            row[k] = v if k == "SNP" else _float(v)
        rows.append(row)
    return rows


# --- step 1: index variants (top_loci.py / gcta.get_conditional_top_loci) --


def select_index_variants(rows, slct) -> "list[dict]":
    """The conditionally independent signals on one chromosome. `rows` are that
    chromosome's prepared sumstats; `slct(gws_rows)` runs `--cojo-slct` and
    returns the `.jma.cojo` text (None when GCTA produced none). The
    reference's short-cuts: no genome-wide-significant variant -> nothing;
    exactly one -> it is the index without running GCTA."""
    gws = [r for r in rows if r["pValue"] <= GWS_P]
    if not gws:
        return []
    if len(gws) == 1:
        return gws
    selected = {r["SNP"] for r in parse_cojo_table(slct(gws))}
    return [r for r in rows if r["dbSNP"] in selected]


# --- step 2: conditional analysis around one index variant -----------------


def window(rows, pos: int, kb: int) -> "list[dict]":
    lo, hi = pos - 1000 * kb, pos + 1000 * kb
    return [r for r in rows if lo <= r["position"] <= hi]


def condition_list(index_rsid: str, window_rows, index_rsids) -> "list[str]":
    """The other index variants inside the window, in window (position) order."""
    wanted = set(index_rsids) - {index_rsid}
    return [r["dbSNP"] for r in window_rows if r["dbSNP"] in wanted]


def conditional_stats(window_rows, cma_text: "str | None") -> "list[dict]":
    """Attach `.cma.cojo` bC/bC_se/pC to the window rows as beta_cond/se_cond/
    p_cond (inner join on rsID, like merge_conditional_w_sumstats). No report
    -> no rows, which is how the reference ends up with no credible set."""
    by_rsid = {r["SNP"]: r for r in parse_cojo_table(cma_text)}
    out = []
    for r in window_rows:
        c = by_rsid.get(r["dbSNP"])
        if c is None or None in (c.get("bC"), c.get("bC_se"), c.get("pC")):
            continue
        row = dict(r)
        row.update(beta_cond=c["bC"], se_cond=c["bC_se"], p_cond=c["pC"])
        out.append(row)
    return out


def marginal_as_conditional(rows) -> "list[dict]":
    out = []
    for r in rows:
        row = dict(r)
        row.update(beta_cond=r["beta"], se_cond=r["stdErr"], p_cond=r["pValue"])
        out.append(row)
    return out


# --- step 3: Wakefield ABF credible set (credible_set.calc_credible_sets) ---


def _log_abf(p_cond: float, eaf: float, n: float) -> float:
    p = p_cond if p_cond > 0 else sys.float_info.min
    z = abs(_NORMAL.inv_cdf(p / 2.0))
    maf = min(eaf, 1.0 - eaf)
    v = 1.0 / (2.0 * n * maf * (1.0 - maf))
    r = PRIOR_SD ** 2 / (PRIOR_SD ** 2 + v)
    return 0.5 * (math.log(1.0 - r) + r * z * z)


def _log_sum(values) -> float:
    m = max(values)
    return m + math.log(sum(math.exp(v - m) for v in values))


def credible_set(rows, pp_threshold: float = PP_THRESHOLD) -> "list[dict]":
    """Posterior probabilities from the conditional p-values (quantitative-
    trait ABF, prior sd 0.15), 95% and 99% credible-set membership by
    cumulative posterior, keeping rows in either set with posterior above
    `pp_threshold`. Rows need p_cond, eaf and n. Returned in position order
    with logABF / postprob / postprob_cumsum / is95 / is99 added."""
    if not rows:
        return []
    scored = []
    for r in rows:
        row = dict(r)
        row["logABF"] = _log_abf(r["p_cond"], r["eaf"], r["n"])
        scored.append(row)
    total = _log_sum([r["logABF"] for r in scored])
    scored.sort(key=lambda r: -r["logABF"])
    cum = 0.0
    for r in scored:
        r["postprob"] = math.exp(r["logABF"] - total)
        cum += r["postprob"]
        r["postprob_cumsum"] = cum
    # The set is every row up to and including the first one that pushes the
    # cumulative posterior past the level (all rows if none does).
    for level, flag in ((0.95, "is95"), (0.99, "is99")):
        idx = next((i for i, r in enumerate(scored) if r["postprob_cumsum"] > level),
                   len(scored) - 1)
        for i, r in enumerate(scored):
            r[flag] = i <= idx
    kept = [r for r in scored if (r["is95"] or r["is99"]) and r["postprob"] > pp_threshold]
    kept.sort(key=lambda r: r["position"])
    return kept


# --- locus labels for the portal picker -------------------------------------


def merge_index_variants_into_loci(index_rows, kb: int = COJO_WINDOW_KB) -> "dict[str, str]":
    """rsID -> locus label (`chr4:68.1-75.3Mb`) from a chained merge of one
    chromosome's index variants: consecutive index variants within `kb` of
    each other share a locus."""
    ordered = sorted(index_rows, key=lambda r: r["position"])
    groups: "list[list[dict]]" = []
    for r in ordered:
        if groups and r["position"] - groups[-1][-1]["position"] <= 1000 * kb:
            groups[-1].append(r)
        else:
            groups.append([r])
    labels = {}
    for g in groups:
        lo, hi = g[0]["position"] / 1e6, g[-1]["position"] / 1e6
        label = f'chr{g[0]["chromosome"]}:{lo:.1f}-{hi:.1f}Mb'
        for r in g:
            labels[r["dbSNP"]] = label
    return labels


# --- the whole method, records in -> portal-shaped rows out -----------------


def _fine_map_index(index: dict, chrom_rows, index_rsids, chrom: str, gcta) -> "list[dict]":
    """Steps 2 + 3 for one index variant (run_credible_set_for_locus)."""
    cojo_rows = window(chrom_rows, index["position"], COJO_WINDOW_KB)
    cond = condition_list(index["dbSNP"], cojo_rows, index_rsids)
    if cond:
        cma = gcta.cond(chrom, cojo_rows, cond)
        if cma is None:
            print(f'WARNING: no conditional GCTA output for {index["dbSNP"]}; '
                  f"skipping its credible set")
        conditioned = conditional_stats(cojo_rows, cma)
    else:
        conditioned = marginal_as_conditional(cojo_rows)
    fm_rows = window(conditioned, index["position"], FM_WINDOW_KB)
    return credible_set(fm_rows)


def derive_credible_sets(records, guid: str, dataset: str, *, gcta,
                         ancestry: "str | None" = None,
                         genome_build: "str | None" = None,
                         rsid_lookup=None):
    """Derive credible sets from a dataset's association records.

    `gcta` runs GCTA: `slct(chrom, gws_rows) -> jma_text | None` and
    `cond(chrom, window_rows, cond_rsids) -> cma_text | None`, plus optional
    `ensure_panel(chrom)` / `release_panel(chrom)` called around each
    chromosome's work. `rsid_lookup` maps varIds without an upload rsID to
    one (the dbSNP-common fallback). Returns (variant_rows, set_rows) shaped
    like the portal's credible-variants / credible-sets records.
    """
    candidates = [dict(r) for r in records if r.get("pValue") is not None]
    if not any(r.get("eaf") is not None for r in candidates) \
            or not any(r.get("n") is not None for r in candidates):
        print("skipping derived credible sets: the upload carries no effect-allele "
              "frequency or no sample size, which the ABF needs")
        return [], []

    missing = {_var_id(r) for r in candidates if not r.get("dbSNP")}
    if missing and rsid_lookup is not None:
        found = rsid_lookup(missing)
        for r in candidates:
            if not r.get("dbSNP"):
                rsid = found.get(_var_id(r))
                if rsid:
                    r["dbSNP"] = rsid

    rows = prepare_sumstats(candidates, genome_build)
    by_chrom: "dict[str, list[dict]]" = {}
    for r in rows:
        by_chrom.setdefault(r["chromosome"], []).append(r)
    chroms = sorted((c for c, rs in by_chrom.items() if any(r["pValue"] <= GWS_P for r in rs)),
                    key=chrom_rank)
    if ancestry:
        print(f"deriving credible sets for ancestry {ancestry} against the "
              f"aggregator's {os.path.basename(PANEL_PREFIX)} LD panel")

    workers = int(os.getenv("VS_GCTA_WORKERS") or os.cpu_count() or 1)
    results: "list[tuple[dict, str, list[dict]]]" = []   # (index, locus, kept rows)
    for chrom in chroms:
        chrom_rows = sorted(by_chrom[chrom], key=lambda r: r["position"])
        if hasattr(gcta, "ensure_panel"):
            gcta.ensure_panel(chrom)
        try:
            index_rows = select_index_variants(chrom_rows, lambda gws: gcta.slct(chrom, gws))
            print(f"chr{chrom}: {len(index_rows)} COJO index variant(s)")
            index_rsids = [r["dbSNP"] for r in index_rows]
            loci = merge_index_variants_into_loci(index_rows)
            with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
                futures = [pool.submit(_fine_map_index, idx, chrom_rows, index_rsids, chrom, gcta)
                           for idx in index_rows]
                for idx, fut in zip(index_rows, futures):
                    results.append((idx, loci[idx["dbSNP"]], fut.result()))
        finally:
            if hasattr(gcta, "release_panel"):
                gcta.release_panel(chrom)

    results.sort(key=lambda t: (chrom_rank(t[0]["chromosome"]), t[0]["position"]))
    variant_rows: "list[dict]" = []
    set_rows: "list[dict]" = []
    for index, locus, kept in results:
        if not kept:
            continue
        set_id = f'chr{index["chromosome"]}:{index["position"]} {index["dbSNP"]}'
        start = kept[0]["position"]
        end = kept[-1]["position"] + 1
        for r in kept:
            row = {
                "phenotype": guid,
                "credibleSetId": set_id,
                "dataset": dataset,
                "varId": _var_id(r),
                "chromosome": r["chromosome"],
                "position": r["position"],
                "reference": r["reference"],
                "alt": r["alt"],
                "pValue": r["pValue"],
                "beta": r["beta"],
                "stdErr": r["stdErr"],
                "n": r["n"],
                "dbSNP": r["dbSNP"],
                "eaf": r["eaf"],
                "betaConditioned": r["beta_cond"],
                "stdErrConditioned": r["se_cond"],
                "pValueConditioned": r["p_cond"],
                "logABF": r["logABF"],
                "posteriorProbability": r["postprob"],
                "posteriorCumulative": r["postprob_cumsum"],
                "in95CredibleSet": r["is95"],
                "in99CredibleSet": r["is99"],
                "leadSNP": r["dbSNP"] == index["dbSNP"],
                "alignment": _sign(r["beta"] * index["beta"]),
                "source": SOURCE,
            }
            if ancestry:
                row["ancestry"] = ancestry
            variant_rows.append(row)
        set_row = {
            "phenotype": guid,
            "credibleSetId": set_id,
            "dataset": dataset,
            "chromosome": index["chromosome"],
            "start": start,
            "end": end,
            "leadVarId": _var_id(index),
            "leadPosition": index["position"],
            "locus": locus,
            "method": METHOD,
            "source": SOURCE,
        }
        if ancestry:
            set_row["ancestry"] = ancestry
        set_rows.append(set_row)
    return variant_rows, set_rows


# --- production GCTA runner + dbSNP fallback --------------------------------


def _ensure_download(s3, key: str, dest: str, bucket: str = CLUMPING_BUCKET) -> str:
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = f"{dest}.partial"
        s3.download_file(bucket, key, tmp)
        os.rename(tmp, dest)
    return dest


class GctaRunner:
    """Runs GCTA-COJO against the aggregator's per-chromosome LD panel, with
    the reference's parameters (gcta.py in the finemapping package). Panel
    files are fetched per chromosome and released afterwards: the whole panel
    is ~56 GB, one chromosome at most ~5 GB, and the Fargate disk is 20 GB."""

    def __init__(self, bucket: str = CLUMPING_BUCKET, workdir: str = CLUMPING_DIR,
                 gcta_bin: str = GCTA_BIN):
        self.bucket = bucket
        self.workdir = workdir
        self.gcta_bin = gcta_bin
        self._s3 = None

    def _s3_client(self):
        if self._s3 is None:
            import boto3  # deferred so pure-logic callers never need it
            self._s3 = boto3.client("s3")
        return self._s3

    def _panel(self, chrom: str) -> str:
        return os.path.join(self.workdir, "panel", f"{os.path.basename(PANEL_PREFIX)}.{chrom}")

    def ensure_panel(self, chrom: str) -> str:
        prefix = self._panel(chrom)
        for ext in ("bed", "bim", "fam"):
            _ensure_download(self._s3_client(), f"{PANEL_PREFIX}.{chrom}.{ext}",
                             f"{prefix}.{ext}", bucket=self.bucket)
        return prefix

    def release_panel(self, chrom: str) -> None:
        prefix = self._panel(chrom)
        for ext in ("bed", "bim", "fam"):
            try:
                os.remove(f"{prefix}.{ext}")
            except FileNotFoundError:
                pass

    def _run(self, chrom: str, rows, extra_args: "list[str]", tag: str,
             report_ext: str, cond_rsids=None) -> "str | None":
        workdir = tempfile.mkdtemp(prefix=f"gcta-{tag}-", dir=self.workdir)
        try:
            ma = os.path.join(workdir, "in.ma")
            snplist = os.path.join(workdir, "in.snplist")
            with open(ma, "w") as f:
                f.write("\n".join(ma_lines(rows)) + "\n")
            with open(snplist, "w") as f:
                f.write("".join(r["dbSNP"] + "\n" for r in rows))
            argv = [self.gcta_bin, "--bfile", self._panel(chrom), "--chr", str(chrom),
                    "--extract", snplist, "--cojo-file", ma]
            if cond_rsids is not None:
                cond = os.path.join(workdir, "cond.txt")
                with open(cond, "w") as f:
                    f.write("".join(rs + "\n" for rs in cond_rsids))
                argv += ["--cojo-cond", cond]
            out = os.path.join(workdir, "out")
            argv += extra_args + ["--out", out]
            # Never shell=True: the reference built its command as a string and
            # a `<NA>` in a file prefix turned into a shell redirect.
            cp = subprocess.run(argv, check=False, stdout=subprocess.DEVNULL,
                                stderr=subprocess.STDOUT)
            if cp.returncode != 0:
                print(f"WARNING: GCTA exited {cp.returncode} ({tag}): "
                      f"{_gcta_log_errors(out + '.log')}")
            report = out + report_ext
            if not os.path.isfile(report):
                return None
            with open(report) as f:
                return f.read()
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def slct(self, chrom: str, gws_rows) -> "str | None":
        """`--cojo-slct` on the genome-wide-significant rows; the `.jma.cojo` text."""
        return self._run(chrom, gws_rows, [
            "--maf", str(MIN_MAF), "--cojo-p", str(GWS_P),
            "--cojo-wind", str(COJO_WINDOW_KB), "--cojo-collinear", str(COJO_COLLINEAR),
            "--cojo-slct"], f"slct-chr{chrom}", ".jma.cojo")

    def cond(self, chrom: str, window_rows, cond_rsids) -> "str | None":
        """`--cojo-cond` of the window rows on `cond_rsids`; the `.cma.cojo` text."""
        return self._run(chrom, window_rows, [], f"cond-chr{chrom}", ".cma.cojo",
                         cond_rsids=list(cond_rsids))


def _gcta_log_errors(log_path: str) -> str:
    try:
        with open(log_path) as f:
            lines = [ln.rstrip() for ln in f if "error" in ln.lower()]
        return " | ".join(lines) or "(no error lines in the GCTA log)"
    except OSError:
        return "(no GCTA log written)"


def dbsnp_rsid_lookup(varids: "set[str]") -> "dict[str, str]":
    """varId -> rsID from the aggregator's dbSNP-common map, for uploads that
    carry no rsid column. Streamed and filtered; on any failure (asset or
    access missing) returns {} so derivation degrades to upload-supplied
    rsIDs rather than dying."""
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
              f"using only upload-supplied rsIDs")
        return {}


# --- writing the derived objects --------------------------------------------


def _write_derived(s3, bucket: str, guid: str, variants, sets_) -> None:
    for key, rows in ((credible_variants_key(guid), variants),
                      (credible_sets_key(guid), sets_)):
        body = "".join(json.dumps(r) + "\n" for r in rows)
        s3.put_object(Bucket=bucket, Key=key, Body=body.encode())


def write_derived_credible_sets(s3, bucket: str, records, guid: str, *,
                                dataset: str,
                                ancestry: "str | None" = None,
                                genome_build: "str | None" = None) -> int:
    """Derive and write this dataset's credible sets. Both objects are written
    even when empty, so the indexes run.py builds afterwards give frontend
    queries clean empty results instead of a missing index. Indexing is NOT
    done here: run.py builds the two credible-set indexes once, after the
    uploaded sets (uploaded_credible_sets.sync_uploaded_credible_sets) have
    been written next to these. Returns the number of variant rows."""
    variants, sets_ = derive_credible_sets(
        records, guid, dataset, gcta=GctaRunner(), ancestry=ancestry,
        genome_build=genome_build, rsid_lookup=dbsnp_rsid_lookup)
    _write_derived(s3, bucket, guid, variants, sets_)
    return len(variants)


def clear_derived_credible_sets(s3, bucket: str, guid: str) -> None:
    """Write both derived objects empty: used when a dataset has uploaded
    credible sets (which take precedence), so the next index build drops any
    previously derived rows."""
    _write_derived(s3, bucket, guid, [], [])
