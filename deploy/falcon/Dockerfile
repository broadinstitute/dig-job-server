# FALCON (Rust engine) packaged for AWS Batch as a dig-job-server method.
#
# Build from the repository root:
#   ./deploy/falcon/deploy.sh --falcon-sha <commit>
#
# The FALCON engine lives in a separate, private repository. deploy.sh clones it
# on the host at the commit given by --falcon-sha and places it under
# deploy/falcon/engine/; this file copies from there. The engine version is
# therefore an explicit, reviewable pin rather than "whatever happened to be
# checked out", and it is what each run's provenance is stamped with.
#
# NOTE: this Dockerfile has its own ignore file, deploy/falcon/Dockerfile.dockerignore.
# The repository root .dockerignore excludes everything but variant_sifter_pipeline
# to keep that image's context small; BuildKit prefers the per-Dockerfile file, so
# both images get a tight context without either widening the other's.

# ==========================================
# Stage 1: Builder
# ==========================================
FROM rust:1.90-bookworm AS builder

ARG FALCON_SHA
RUN test -n "$FALCON_SHA" || { echo "FALCON_SHA build-arg is required" >&2; exit 1; }

WORKDIR /build

# The engine source is checked out on the HOST by deploy.sh, at the pinned SHA,
# and copied in. It is not cloned here: the FALCON repository is private, and a
# builder container has no credentials. deploy.sh does the clone where the
# developer's existing git auth already works -- the same shape as the bundled
# reference data, which fetch-reference.sh puts into the context.

# Dependencies first, against a stub main, so a source-only change does not
# refetch and rebuild the whole crate graph.
COPY deploy/falcon/engine/falcon-rs/Cargo.toml ./falcon-rs/Cargo.toml
RUN mkdir -p falcon-rs/src \
    && echo 'fn main() {}' > falcon-rs/src/main.rs \
    && echo '' > falcon-rs/src/lib.rs \
    && cargo build --release --manifest-path falcon-rs/Cargo.toml \
    && rm -rf falcon-rs/src

COPY deploy/falcon/engine/falcon-rs/src ./falcon-rs/src
RUN touch falcon-rs/src/main.rs falcon-rs/src/lib.rs \
    && cargo build --release --manifest-path falcon-rs/Cargo.toml \
    && strip falcon-rs/target/release/falcon

# s5cmd moves the ~39 GB LD reference far faster than `aws s3 cp`.
ARG S5CMD_VERSION=2.2.2
RUN curl -fsSL "https://github.com/peak/s5cmd/releases/download/v${S5CMD_VERSION}/s5cmd_${S5CMD_VERSION}_Linux-64bit.tar.gz" \
      | tar -xz -C /usr/local/bin s5cmd \
    && s5cmd version

# ==========================================
# Stage 2: Runtime
# ==========================================
FROM debian:bookworm-slim AS runtime

# python3-minimal alone omits libpython3.11-stdlib under --no-install-recommends,
# which drops gzip/json/dataclasses/statistics and breaks the converter at import.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        procps \
        time \
        python3-minimal \
        libpython3.11-stdlib \
    && rm -rf /var/lib/apt/lists/*

# Small reference data, baked in: genes (677 KB) + V2G (194 MB) +
# annotations (107 MB). Placed high because it changes far less often than
# anything below it. Populate the build context first:
#   ./deploy/falcon/fetch-reference.sh deploy/falcon/reference
# The 39 GB LD reference is deliberately NOT bundled -- Fargate re-pulls the
# image per task, so it would be slower than the runtime s5cmd download.
COPY deploy/falcon/reference /opt/falcon-ref
ENV FALCON_REF_DIR=/opt/falcon-ref

# The converter, plus the single validator module it imports SCHEMA_VERSION
# from. job_server/falcon.py is stdlib-only, so carrying it costs nothing and
# makes it impossible for the manifest producer and validator to drift.
COPY falcon_prep /opt/prep/falcon_prep
COPY job_server/__init__.py /opt/prep/job_server/__init__.py
COPY job_server/falcon.py /opt/prep/job_server/falcon.py
ENV PYTHONPATH=/opt/prep

# Config template read by the entrypoint's dataset mode.
COPY deploy/falcon/configs /opt/configs

COPY --from=builder /build/falcon-rs/target/release/falcon /usr/local/bin/falcon
COPY --from=builder /usr/local/bin/s5cmd /usr/local/bin/s5cmd
COPY deploy/falcon/falcon-batch.sh /usr/local/bin/falcon-batch

RUN chmod +x /usr/local/bin/falcon-batch /usr/local/bin/falcon /usr/local/bin/s5cmd

# Provenance: the ENGINE commit, stamped into every run's log and metrics line.
ARG FALCON_SHA
ENV FALCON_GIT_SHA=${FALCON_SHA} \
    FALCON_ENGINE=falcon-rs \
    FALCON_BIN=falcon
LABEL org.opencontainers.image.revision=${FALCON_SHA} \
      org.opencontainers.image.title=falcon-rs

# Where inputs are staged and results are written. On Fargate this is the
# task's ephemeral volume; the whole-genome LD reference needs ~40 GB free.
ENV FALCON_WORK_DIR=/scratch
WORKDIR /scratch

ENTRYPOINT ["/usr/local/bin/falcon-batch"]
