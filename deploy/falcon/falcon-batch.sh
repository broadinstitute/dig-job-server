#!/usr/bin/env bash
#
# AWS Batch entrypoint for FALCON — shared by the Python and Rust images.
#
#   falcon-batch s3://bucket/run/config.ini [extra falcon flags...]
#   falcon-batch --username U --dataset D
#
# Config mode (first form): one positional argument names a FALCON .ini whose
# paths may be s3:// URIs. Every s3:// value is staged to local disk, the
# config is rewritten to point at the local copies, the engine runs, and
# everything matching the out-base-name is uploaded back to the prefix the
# config asked for. This is the research/benchmark path -- every reproduction
# command in docker/RESULTS.md depends on it, and it is unchanged by dataset
# mode.
#
# Dataset mode (second form): stages a dig-job-server upload from
# s3://.../userdata/U/genetic/D/raw/, converts it to FALCON sumstats (only
# chromosomes with |Z| >= zero-snp-thr survive), renders
# /opt/configs/job-server.ini.tmpl around the result, and falls through into
# config mode with that rendered config. Results land under
# s3://.../userdata/U/genetic/D/falcon/.
#
# Both images run THIS script, so staging, upload and timing are byte-identical
# between engines and the only thing a head-to-head run measures is the engine
# itself. The engine is selected by $FALCON_BIN, baked in at build time.
#
# Only the chromosomes named by chr-to-update are downloaded. That matters: the
# whole-genome LD reference is ~39 GB but a single chromosome is 0.3-3.8 GB.
#
# Environment:
#   FALCON_BIN         engine command (default "falcon"; py image sets
#                      "python -m src.falcon.cli")
#   FALCON_ENGINE      label for logs/metrics ("falcon-rs" | "falcon-py")
#   FALCON_GIT_SHA     source commit the image was built from (stamped at build)
#   FALCON_CHR         override chr-to-update (e.g. "22" or "1-22")
#   FALCON_WORK_DIR    staging root (default /scratch)
#   FALCON_SKIP_UPLOAD set to 1 to leave results on local disk
#   RAYON_NUM_THREADS  cap falcon-rs worker threads (default: all vCPUs)
#   JOB_SERVER_BUCKET  dataset mode only: bucket holding userdata/ and the
#                      dbSNP map (default "dig-ldsc-server")
#
# In an array job, AWS_BATCH_JOB_ARRAY_INDEX selects one chromosome from
# chr-to-update, so N shards cover the genome. falcon-rs processes chromosomes
# independently and `.wg.*` is a plain concatenation, so this is safe.

set -Eeuo pipefail

readonly WORK_DIR="${FALCON_WORK_DIR:-/scratch}"
readonly INPUT_DIR="$WORK_DIR/inputs"
readonly RESULT_DIR="$WORK_DIR/results"
readonly ENGINE="${FALCON_ENGINE:-falcon}"
readonly GIT_SHA="${FALCON_GIT_SHA:-unknown}"

log() { printf '[falcon-batch] %s\n' "$*" >&2; }
die() { printf '[falcon-batch] ERROR: %s\n' "$*" >&2; exit 1; }

trim() {
    local s="$1"
    s="${s#"${s%%[![:space:]]*}"}"
    printf '%s' "${s%"${s##*[![:space:]]}"}"
}

now() { date +%s.%N; }

elapsed() { awk -v a="$1" -v b="$2" 'BEGIN { printf "%.1f", b - a }'; }

# --- S3 helpers -------------------------------------------------------------

s3_cp() {
    local src="$1" dst="$2"
    mkdir -p "$(dirname "$dst")"
    s5cmd --log error cp "$src" "$dst" \
        || die "download failed: $src"
}

# --- chromosome list --------------------------------------------------------

# "1-3,7,9-10" -> "1 2 3 7 9 10"
expand_chroms() {
    local spec="${1//_/}" out=() part lo hi i
    spec="${spec// /}"
    IFS=',' read -r -a parts <<< "$spec"
    for part in "${parts[@]}"; do
        [[ -z "$part" ]] && continue
        if [[ "$part" == *-* ]]; then
            lo="${part%%-*}"; hi="${part##*-}"
            for (( i = lo; i <= hi; i++ )); do out+=("$i"); done
        else
            out+=("$part")
        fi
    done
    printf '%s' "${out[*]}"
}

# Per-chromosome filename pattern for each *-folder key, mirroring
# falcon-rs/src/io/readers.rs::resolve_paths (and its Python counterpart in
# falcon_worker/mixins/io_mixin.py).
folder_pattern() {
    case "$1" in
        ld-folder|exome-ld-folder)             printf '{CHR}.ld.sorted' ;;
        gene-folder)                           printf '{CHR}.genes.loc' ;;
        s2g-folder)                            printf 'cS2G.{CHR}.SGscore' ;;
        sumstats-folder|exome-sumstats-folder) printf '{CHR}.sumstats' ;;
        dentist-folder)                        printf '{CHR}.DENTIST.full.txt' ;;
        *) return 1 ;;
    esac
}

# --- argument handling ------------------------------------------------------

[[ $# -ge 1 ]] || die "usage: falcon-batch <config.ini | s3://.../config.ini> [falcon flags...]"

CONFIG_ARG="$1"; shift
EXTRA_ARGS=("$@")

# The engine command, e.g. "falcon" or "python -m src.falcon.cli".
read -r -a ENGINE_CMD <<< "${FALCON_BIN:-falcon}"

mkdir -p "$INPUT_DIR" "$RESULT_DIR"

T_START="$(now)"

log "engine ${ENGINE} @ ${GIT_SHA} (${ENGINE_CMD[*]})"

# --- dataset mode ------------------------------------------------------------
# `falcon-batch --username U --dataset D` converts a dig-job-server upload and
# runs FALCON on it. Any other first argument is a config path (original mode).
if [[ "$CONFIG_ARG" == --username || "$CONFIG_ARG" == --dataset ]]; then
    set -- "$CONFIG_ARG" "$@"
    JS_USER=""; JS_DATASET=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --username) [[ $# -ge 2 ]] || die "--username requires a value"; JS_USER="$2"; shift 2 ;;
            --dataset)  [[ $# -ge 2 ]] || die "--dataset requires a value"; JS_DATASET="$2"; shift 2 ;;
            *) die "unexpected argument in dataset mode: $1" ;;
        esac
    done
    [[ -n "$JS_USER" ]]    || die "dataset mode requires --username"
    [[ -n "$JS_DATASET" ]] || die "dataset mode requires --dataset"

    [[ -f /opt/configs/job-server.ini.tmpl ]] \
        || die "dataset mode requires the falcon-rs image (no /opt/configs found)"

    JS_ROOT="s3://${JOB_SERVER_BUCKET:-dig-ldsc-server}/userdata/${JS_USER}/genetic/${JS_DATASET}"
    RAW_DIR="$WORK_DIR/raw"
    SUMSTATS_DIR="$WORK_DIR/sumstats"
    mkdir -p "$RAW_DIR" "$SUMSTATS_DIR"

    log "dataset mode: ${JS_USER}/${JS_DATASET}"
    s5cmd --log error cp "$JS_ROOT/raw/*" "$RAW_DIR/" || die "cannot stage raw/"

    DBSNP="$WORK_DIR/dbsnp.csv"
    log "fetching dbSNP GRCh37 map"
    s5cmd --log error cp \
        "s3://${JOB_SERVER_BUCKET:-dig-ldsc-server}/bin/magma/dbSNP_common_GRCh37.csv" \
        "$DBSNP" || die "cannot stage dbSNP map"

    # One source of truth for the Z threshold: the config's own zero-snp-thr.
    ZTHR="$(awk -F= '/^[[:space:]]*zero-snp-thr/ {gsub(/ /,"",$2); print $2}' \
        /opt/configs/job-server.ini.tmpl)"
    [[ -n "$ZTHR" ]] || die "job-server.ini.tmpl has no zero-snp-thr"

    log "converting upload (|Z| >= ${ZTHR})"
    T_PREP_START="$(now)"
    set +e
    PREP_SUMMARY="$(python3 -m falcon_prep.cli \
        --raw-dir "$RAW_DIR" --out-dir "$SUMSTATS_DIR" \
        --dbsnp "$DBSNP" --z-threshold "$ZTHR")"
    PREP_RC=$?
    set -e
    [[ $PREP_RC -eq 0 ]] || { log "conversion failed (rc=$PREP_RC)"; exit "$PREP_RC"; }
    PREP_SECS="$(elapsed "$T_PREP_START" "$(now)")"
    log "conversion finished in ${PREP_SECS}s"
    log "conversion summary: $PREP_SUMMARY"
    printf '%s' "$PREP_SUMMARY" > "$WORK_DIR/prep-summary.json"

    # Only chromosomes that produced variants. The converter writes no file for
    # a chromosome with no significant variants, so this listing IS the set of
    # chromosomes with signal.
    CHRS="$(ls "$SUMSTATS_DIR" | sed 's/\.sumstats$//' | sort -n | paste -sd, -)"
    [[ -n "$CHRS" ]] || die "converter produced no sumstats"

    # sample-size, when the upload's metadata carries an effective N. Absent
    # that, the template's own value stands -- there is nothing dataset-specific
    # to replace it with. (inf-heritability is left at the template's value;
    # see the TODO next to it in job-server.ini.tmpl.)
    EFFECTIVE_N="$(python3 -c '
import json, sys
try:
    with open(sys.argv[1]) as fh:
        n = json.load(fh).get("effective_n")
except (OSError, ValueError):
    n = None
print(int(round(n)) if n is not None else "")
' "$RAW_DIR/metadata" 2>/dev/null || true)"

    CONFIG_ARG="$WORK_DIR/job-server.ini"
    # --- LD chunk selection -------------------------------------------------
    # Fetch only the 1 Mb windows holding significant variants, not the whole
    # 39 GB reference. falcon-rs keeps an LD row only when BOTH its SNPs are in
    # the modelled set, so windows without one contribute nothing. Verified
    # lossless against the monolithic reference on real data: identical usable
    # rows from 35 MB instead of 348 MB on chr22.
    LD_DIR="$WORK_DIR/ld"
    mkdir -p "$LD_DIR"
    CHUNK_LIST="$WORK_DIR/ld-chunks.txt"
    CHUNK_PREFIX="${FALCON_LD_CHUNKS:-s3://falcon-data-center/ld_chunks}"
    # Not every 1 Mb window has a published chunk -- chromosome ends stop short
    # and some interior windows hold no LD -- so list what exists and ask only
    # for that. Requesting a missing key aborts the whole batch download.
    AVAILABLE="$WORK_DIR/ld-available.txt"
    # No --log error here: it suppresses ls output as well as diagnostics.
    s5cmd ls "${CHUNK_PREFIX}/*/*.ld" 2>/dev/null \
        | awk '{print $NF}' > "$AVAILABLE" \
        || die "could not list the chunked LD reference"
    [[ -s "$AVAILABLE" ]] || die "chunked LD reference is empty at ${CHUNK_PREFIX}"
    if ! python3 -m falcon_prep.ldchunks \
            --sumstats-dir "$SUMSTATS_DIR" \
            --prefix "$CHUNK_PREFIX" \
            --available "$AVAILABLE" \
            > "$CHUNK_LIST"; then
        die "could not determine which LD chunks are needed"
    fi
    CHUNK_COUNT="$(wc -l < "$CHUNK_LIST")"
    log "staging ${CHUNK_COUNT} LD chunks (of the whole-genome reference)"
    T_LD_START="$(now)"
    # One s5cmd batch beats one invocation per chunk.
    awk -F'\t' -v d="$LD_DIR" '{print "cp " $1 " " d "/" $2 "/"}' "$CHUNK_LIST" \
        | s5cmd --log error run || die "LD chunk download failed"
    # Concatenate each chromosome's chunks into the {chr}.ld.sorted FALCON
    # expects. Order does not matter -- read_ld_sparse builds a sparse matrix
    # from rows in any order, and `sorted-ld` is declared but never read. Extra
    # header lines are dropped so the file has exactly one.
    for d in "$LD_DIR"/*/; do
        [[ -d "$d" ]] || continue
        c="$(basename "$d")"
        { head -1 "$(find "$d" -name '*.ld' | head -1)"
          find "$d" -name '*.ld' -exec grep -hv '^#' {} +
        } > "$LD_DIR/${c}.ld.sorted"
        rm -rf "$d"
    done
    log "LD staged in $(elapsed "$T_LD_START" "$(now)")s ($(du -sh "$LD_DIR" | cut -f1))"

    sed -e "s|@OUT_BASE@|${JS_ROOT}/falcon/out|" \
        -e "s|@CHR@|${CHRS}|" \
        -e "s|@SUMSTATS@|${SUMSTATS_DIR}/|" \
        /opt/configs/job-server.ini.tmpl > "$CONFIG_ARG"
    {
        printf 's2g-folder = %s/V2G/\n'   "${FALCON_REF_DIR:-/opt/falcon-ref}"
        printf 'gene-folder = %s/genes/\n' "${FALCON_REF_DIR:-/opt/falcon-ref}"
        printf 'ld-folder = %s/\n' "$LD_DIR"
        if [[ -n "$EFFECTIVE_N" ]]; then
            printf 'sample-size = %s\n' "$EFFECTIVE_N"
        fi
    } >> "$CONFIG_ARG"
    [[ -n "$EFFECTIVE_N" ]] && log "sample-size <- effective_n (${EFFECTIVE_N})"
    EXTRA_ARGS=()
fi

RAW_CFG="$WORK_DIR/config.remote.ini"
if [[ "$CONFIG_ARG" == s3://* ]]; then
    log "fetching config $CONFIG_ARG"
    s3_cp "$CONFIG_ARG" "$RAW_CFG"
else
    [[ -f "$CONFIG_ARG" ]] || die "config not found: $CONFIG_ARG"
    cp "$CONFIG_ARG" "$RAW_CFG"
fi

# --- pass 1: resolve the chromosome set ------------------------------------

CHR_SPEC=""
while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" == *"="* ]] || continue
    [[ "$(trim "${line%%=*}")" == "chr-to-update" ]] || continue
    CHR_SPEC="$(trim "${line#*=}")"
done < "$RAW_CFG"

[[ -n "${FALCON_CHR:-}" ]] && CHR_SPEC="$FALCON_CHR"
[[ -n "$CHR_SPEC" ]] || die "config has no chr-to-update and FALCON_CHR is unset"

read -r -a CHROMS <<< "$(expand_chroms "$CHR_SPEC")"

# Array job: this shard takes exactly one chromosome.
SHARD_SUFFIX=""
if [[ -n "${AWS_BATCH_JOB_ARRAY_INDEX:-}" ]]; then
    idx="$AWS_BATCH_JOB_ARRAY_INDEX"
    [[ "$idx" -lt "${#CHROMS[@]}" ]] \
        || die "array index $idx exceeds ${#CHROMS[@]} chromosomes in chr-to-update"
    CHROMS=("${CHROMS[$idx]}")
    CHR_SPEC="${CHROMS[0]}"
    SHARD_SUFFIX=".chr${CHROMS[0]}"
    log "array shard $idx -> chromosome ${CHROMS[0]}"
fi

log "chromosomes: ${CHROMS[*]}"

# --- pass 2: stage inputs and rewrite the config ---------------------------

LOCAL_CFG="$WORK_DIR/config.local.ini"
: > "$LOCAL_CFG"

OUT_S3_PREFIX=""
OUT_BASENAME=""
LOCAL_OUT_BASE=""

T_STAGE_START="$(now)"

while IFS= read -r line || [[ -n "$line" ]]; do
    # Blank lines, comments and section headers pass through untouched.
    if [[ -z "$(trim "$line")" || "$line" =~ ^[[:space:]]*[#\;] || "$line" =~ ^[[:space:]]*\[ ]]; then
        printf '%s\n' "$line" >> "$LOCAL_CFG"
        continue
    fi
    if [[ "$line" != *"="* ]]; then
        printf '%s\n' "$line" >> "$LOCAL_CFG"
        continue
    fi

    key="$(trim "${line%%=*}")"
    val="$(trim "${line#*=}")"

    # chr-to-update may have been narrowed by FALCON_CHR or an array index.
    if [[ "$key" == "chr-to-update" ]]; then
        printf '%s = %s\n' "$key" "$CHR_SPEC" >> "$LOCAL_CFG"
        continue
    fi

    if [[ "$val" != s3://* ]]; then
        printf '%s\n' "$line" >> "$LOCAL_CFG"
        continue
    fi

    case "$key" in
        out-base-name)
            OUT_S3_PREFIX="${val%/*}"
            OUT_BASENAME="${val##*/}"
            LOCAL_OUT_BASE="$RESULT_DIR/$OUT_BASENAME"
            printf '%s = %s\n' "$key" "$LOCAL_OUT_BASE" >> "$LOCAL_CFG"
            log "results -> $OUT_S3_PREFIX/"
            ;;

        *-folder)
            pattern="$(folder_pattern "$key")" \
                || die "no per-chromosome filename pattern known for '$key'"
            dest="$INPUT_DIR/$key"
            mkdir -p "$dest"
            remote="${val%/}"
            for chr in "${CHROMS[@]}"; do
                fname="${pattern//\{CHR\}/$chr}"
                log "staging $key chr$chr"
                s3_cp "$remote/$fname" "$dest/$fname"
            done
            printf '%s = %s/\n' "$key" "$dest" >> "$LOCAL_CFG"
            ;;

        annotations)
            # A prefix (or comma-separated prefixes); falcon appends ".{chrom}".
            local_prefixes=()
            IFS=',' read -r -a annot_specs <<< "$val"
            for spec in "${annot_specs[@]}"; do
                spec="$(trim "$spec")"
                [[ -n "$spec" ]] || continue
                base="${spec##*/}"
                dest="$INPUT_DIR/annotations"
                mkdir -p "$dest"
                for chr in "${CHROMS[@]}"; do
                    log "staging annotation ${base}.${chr}"
                    s3_cp "${spec}.${chr}" "$dest/${base}.${chr}"
                done
                local_prefixes+=("$dest/$base")
            done
            printf '%s = %s\n' "$key" "$(IFS=,; printf '%s' "${local_prefixes[*]}")" >> "$LOCAL_CFG"
            ;;

        *)
            # Any other s3:// value is a single object.
            dest="$INPUT_DIR/$key/${val##*/}"
            log "staging $key"
            s3_cp "$val" "$dest"
            printf '%s = %s\n' "$key" "$dest" >> "$LOCAL_CFG"
            ;;
    esac
done < "$RAW_CFG"

T_STAGE_END="$(now)"
STAGE_SECS="$(elapsed "$T_STAGE_START" "$T_STAGE_END")"
INPUT_BYTES="$(du -sb "$INPUT_DIR" 2>/dev/null | cut -f1 || echo 0)"
log "staged $(numfmt --to=iec "$INPUT_BYTES" 2>/dev/null || echo "$INPUT_BYTES")B in ${STAGE_SECS}s"

# A local out-base-name still needs a home for the upload step to find.
if [[ -z "$LOCAL_OUT_BASE" ]]; then
    LOCAL_OUT_BASE="$(grep -E '^[[:space:]]*out-base-name' "$LOCAL_CFG" | tail -1 | sed 's/[^=]*=//' | xargs || true)"
    [[ -n "$LOCAL_OUT_BASE" ]] || die "config has no out-base-name"
    log "out-base-name is local ($LOCAL_OUT_BASE); results will not be uploaded"
fi
mkdir -p "$(dirname "$LOCAL_OUT_BASE")"

# --- run --------------------------------------------------------------------

VCPUS="$(nproc)"
CPU_MODEL="$(awk -F': ' '/model name/ {print $2; exit}' /proc/cpuinfo 2>/dev/null || echo unknown)"
MEM_MB="$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo 2>/dev/null || echo 0)"
log "host: ${VCPUS} vCPU / ${MEM_MB} MB | ${CPU_MODEL}"
log "running ${ENGINE_CMD[*]} (RAYON_NUM_THREADS=${RAYON_NUM_THREADS:-unset})"

T_RUN_START="$(now)"
set +e
/usr/bin/time -v -o "$WORK_DIR/time.txt" \
    "${ENGINE_CMD[@]}" --config-file "$LOCAL_CFG" "${EXTRA_ARGS[@]}"
RUN_RC=$?
set -e
T_RUN_END="$(now)"
RUN_SECS="$(elapsed "$T_RUN_START" "$T_RUN_END")"

PEAK_RSS_KB="$(awk -F': ' '/Maximum resident set size/ {print $2}' "$WORK_DIR/time.txt" 2>/dev/null || echo 0)"

if [[ $RUN_RC -ne 0 ]]; then
    log "${ENGINE} exited $RUN_RC after ${RUN_SECS}s - dumping ${LOCAL_OUT_BASE}.wg.log"
    tail -n 200 "${LOCAL_OUT_BASE}.wg.log" 2>/dev/null || log "(no wg.log written)"
    exit "$RUN_RC"
fi

log "${ENGINE} finished in ${RUN_SECS}s (peak RSS $(( PEAK_RSS_KB / 1024 )) MB)"

# The engine's own end-of-run wall clock, straight from its log.
TOTAL_TIME_LINE="$(grep -h 'Total Time' "${LOCAL_OUT_BASE}.wg.log" 2>/dev/null | tail -1 || true)"
[[ -n "$TOTAL_TIME_LINE" ]] && log "engine reports: $TOTAL_TIME_LINE"

# --- upload -----------------------------------------------------------------

T_UP_START="$(now)"
UPLOAD_BYTES=0
if [[ -n "$OUT_S3_PREFIX" && "${FALCON_SKIP_UPLOAD:-0}" != "1" ]]; then
    shopt -s nullglob
    for f in "${LOCAL_OUT_BASE}"*; do
        [[ -f "$f" ]] || continue
        name="${f##*/}"
        # Shards must not overwrite each other's whole-genome rollups.
        if [[ -n "$SHARD_SUFFIX" && "$name" == *.wg.* ]]; then
            name="${name/.wg./${SHARD_SUFFIX}.wg.}"
        fi
        s5cmd --log error cp "$f" "$OUT_S3_PREFIX/$name" || die "upload failed: $f"
        UPLOAD_BYTES=$(( UPLOAD_BYTES + $(stat -c%s "$f") ))
    done
    shopt -u nullglob
    log "uploaded $(numfmt --to=iec "$UPLOAD_BYTES" 2>/dev/null || echo "$UPLOAD_BYTES")B to $OUT_S3_PREFIX/"
fi
T_UP_END="$(now)"
UPLOAD_SECS="$(elapsed "$T_UP_START" "$T_UP_END")"
TOTAL_SECS="$(elapsed "$T_START" "$T_UP_END")"

# --- manifest (dataset mode only) -------------------------------------------
# Binds this run to the dataset's GWAS file by SHA-256 so the server can run
# the same validation it already runs for local FALCON runs. Must land at
# exactly {JS_ROOT}/falcon/manifest.json -- that's where falcon_finalize reads
# it via s3.get_falcon_s3_prefix(username, dataset, "manifest.json").
if [[ -n "${JS_ROOT:-}" ]]; then
    # The only point in the pipeline that can observe FALCON having dropped every
    # variant (unmatched rsIDs are discarded without warning). Refuse to attest
    # to results that do not exist.
    [[ -s "${LOCAL_OUT_BASE}.wg.genes" ]] \
        && [[ "$(wc -l < "${LOCAL_OUT_BASE}.wg.genes")" -gt 1 ]] \
        || die "FALCON produced no gene results; refusing to write a manifest"

    UPLOAD_FILE="$(printf '%s' "$PREP_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["upload_file"])')"
    [[ -n "$UPLOAD_FILE" ]] || die "converter did not report which upload file it read"
    python3 - "$JS_DATASET" "$GIT_SHA" "$RAW_DIR/$UPLOAD_FILE" "$UPLOAD_FILE" \
             "$CHRS" "${JS_ROOT}/falcon/out" "$WORK_DIR/prep-summary.json" \
             <<'PY' > "$WORK_DIR/manifest.json"
import json, sys
from falcon_prep.manifest import build_manifest
dataset, sha, path, fname, chrs, out_base, prep_path = sys.argv[1:8]
print(json.dumps(build_manifest(
    dataset_name=dataset, falcon_version=sha,
    input_path=path, input_filename=fname,
    split_chromosomes=[int(c) for c in chrs.split(",") if c],
    out_base_name=out_base,
    prep_summary=json.load(open(prep_path)),
)))
PY
    if [[ "${FALCON_SKIP_UPLOAD:-0}" == "1" ]]; then
        log "FALCON_SKIP_UPLOAD=1 - manifest written to $WORK_DIR/manifest.json, not uploaded"
    else
        s5cmd --log error cp "$WORK_DIR/manifest.json" "$JS_ROOT/falcon/manifest.json" \
            || die "manifest upload failed"
        log "wrote manifest.json for server-side validation"
    fi
fi

# One machine-readable line so a run's cost and provenance can be reconstructed
# from the log alone.
printf 'FALCON_METRICS {"engine":"%s","git_sha":"%s","chromosomes":"%s","vcpus":%s,"mem_mb":%s,"cpu_model":"%s","stage_seconds":%s,"run_seconds":%s,"upload_seconds":%s,"total_seconds":%s,"input_bytes":%s,"output_bytes":%s,"peak_rss_mb":%s}\n' \
    "$ENGINE" "$GIT_SHA" "$CHR_SPEC" "$VCPUS" "$MEM_MB" "$CPU_MODEL" \
    "$STAGE_SECS" "$RUN_SECS" "$UPLOAD_SECS" "$TOTAL_SECS" \
    "$INPUT_BYTES" "$UPLOAD_BYTES" "$(( PEAK_RSS_KB / 1024 ))"
