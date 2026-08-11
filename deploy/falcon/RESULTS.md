# FALCON job-server integration: measured results

Runtime and correctness for FALCON run as a dig-job-server method. The
falcon-rs vs falcon-py engine benchmark lives with the engine, in the FALCON
repository's `docker/RESULTS.md` — this file covers the integration only.

## Job-server dataset mode: first end-to-end run (2026-08-07)

`falcon-batch --username ngth --dataset Kurki2023_FinnGen_EU` — a real
dig-job-server upload converted and run end to end, results and a
server-validatable manifest written back to the job-server bucket.

| | |
| :--- | ---: |
| Job wall clock | 561.9 s (9m22s) |
| S3 staging (38.7 GB LD + 1.2 GB dbSNP) | 245.6 s |
| Conversion (20,069,063 rows) | 83.1 s |
| FALCON (21 chromosomes) | 208.4 s |
| Upload (30 MB, 88 objects) | 11.9 s |
| Peak RSS | 6,759 MB |
| Shape | 16 vCPU / 32 GB Fargate |

Converter counts: 20,069,063 rows in, 14,926 at |Z| >= 5, **13,933 resolved
against dbSNP (93.35%)**, 727,127 unparseable. chr21 produced no significant
variants and is correctly absent from `chr-to-update`.

**The manifest binding was verified independently.** The 864 MB upload was
re-hashed straight from S3 and its SHA-256 matches the manifest's `input_sha256`
exactly, so the attestation reflects the bytes actually processed rather than
restating metadata. `job_server.falcon.validate_manifest` accepts the manifest;
a negative control with the wrong dataset name is refused with
`dataset_name_mismatch`.

### Staging still costs more than the science

245.6 s fetching LD against 208.4 s running FALCON — and of the 38.7 GB fetched,
this trait's significant variants touch only ~4.15 GB (296 of 2,733 1 Mb
chunks). Chunk selection would cut the job to roughly 360 s, a 39% reduction,
against the 45% modelled earlier. Not implemented; see the LD chunk selection
note below.

### Infrastructure note

The first attempt failed at upload with `AccessDenied`: `FalconJobRole` had
`s3:GetObject` on `*` but `s3:PutObject` only on `dig-falcon-results/*`, while
dataset mode writes to `dig-ldsc-server`. The role's inline `S3Write` policy was
extended to `arn:aws:s3:::dig-ldsc-server/userdata/*/genetic/*/falcon/*` —
scoped so a bug cannot overwrite anyone's `raw/` upload.

**That change is CloudFormation drift.** `FalconJobRole` is owned by the
`falcon-batch` stack, so the next stack update reverts it and dataset-mode jobs
resume failing with the same error. The durable fix belongs in the stack
template.

## Confirmation after relocating to dig-job-server (2026-08-10)

The same dataset re-run from the relocated build, engine pinned at `e709223`:

| | Pre-move (`15f8655`) | Post-move (`e709223`) |
| :--- | ---: | ---: |
| resolved | 13,929 | 13,929 |
| duplicates | 4 | 4 |
| rsid_resolution_rate | 0.9332 | 0.9332 |
| input_sha256 | 255e7b9c… | 255e7b9c… |

Per-chromosome counts identical across all 21 chromosomes. The move is
behaviour-preserving.

`falcon_version` differs by design: it now records the FALCON **engine** commit
rather than the harness commit, since the harness lives in this repository and
the engine is pinned by `deploy.sh --falcon-sha`.

### What `duplicates` measures

The run before the fix wave reported 13,933 resolved and no duplicate count.
Four rsIDs in this dataset appear more than once — on chromosomes 2, 7, 12 and
17. falcon-rs keys its sumstats maps by rsID, so before deduplication it
silently kept whichever row was written last, which at a multi-allelic site can
select the opposite effect direction. Those four are now resolved
deterministically by largest |Z|, and counted.

## LD chunk selection (2026-08-11)

Same dataset, same engine commit, chunked LD instead of whole-chromosome files:

| | Whole-chromosome LD | Chunked LD |
| :--- | ---: | ---: |
| Job wall clock | 590 s | **315 s** |
| FALCON engine time | 208 s | **171 s** |
| S3 staging (generic loop) | 245 s | 0.2 s |
| resolved / duplicates / rate | 13,929 / 4 / 0.9332 | identical |

**47% faster**, against the 39% projected from chunk sizes alone. The engine got
faster too, which the projection did not anticipate: parsing ~4 GB of LD instead
of 38.7 GB is less work inside `read_ld_sparse`, not only less transfer.

`stage_seconds` now reads ~0 because LD is fetched by the chunk block rather
than the generic `*-folder` staging loop. The cost moved and shrank; it did not
disappear, and it is logged separately.

### Correctness

Verified against the reference rather than argued from the code. Taking the 162
variants FALCON actually modelled on chr22 in the previous run, the usable LD
rows — those with **both** SNPs in the modelled set, which is exactly what
`read_ld_sparse` keeps — are identical from either source: 11,602 rows, nothing
missing, nothing extra, from 35.3 MB of chunks against 347.6 MB monolithic. The
assembled `{chr}.ld.sorted` was checked as well as the raw chunks, since
concatenation is where a header or ordering fault would hide.

### Not every window has a chunk

Published windows stop at each chromosome's end and have occasional interior
gaps. This dataset contains a chr20 variant at 64.5 Mb — past chr20's 63 Mb end
— so its window has no chunk. Requesting a missing key aborts the whole batch
download, so the entrypoint lists what exists, intersects, and reports how many
windows were skipped. Those variants have no LD data and FALCON would drop them
regardless; the point is that it is stated rather than silent.
