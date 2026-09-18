# Runtime for the gwas-ce-variant-sifter Batch job: builds the p-value-filtered
# associations for one uploaded GWAS and indexes them into the gwas_ce bioindex.
# Deliberately separate from the GWAS-CE app image — bioindex pins Pydantic v1,
# the app uses v2. This container does NOT import job_server.
FROM python:3.10-slim

WORKDIR /app

# git is needed to install bioindex from source (matches the deployed portal
# runtime); curl/unzip/ca-certificates fetch the GCTA binary below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# GCTA 1.95.2 (COJO) for the derived credible sets: the same version and URL the
# aggregator's finemapping pipeline pins in versions.env. Baked into the image so
# a job never depends on the yanglab site being up. sha256 computed 2026-09-18
# from that URL. Note 1.95.2 ships `gcta` (older releases were `gcta64`), and
# that file is an AppImage: it needs FUSE to run, which Fargate has not. So it
# is unpacked at build time (--appimage-extract needs no FUSE) and the inner
# binary + its bundled MKL/GSL/gomp libraries are installed under /opt/gcta,
# keeping the binary's ../lib rpath layout. credible_sets.py reads the path
# from VS_GCTA_BIN, defaulting to /opt/gcta/gcta.
ARG GCTA_VERSION=1.95.2
ARG GCTA_SHA256=3e6683ae8c0f91fa09b21c5d45e8c330b6c24824076455dd7b7d5f2dbdfe7d89
RUN set -eux; \
    cd /tmp; \
    curl -fsSL -o gcta.zip "https://yanglab.westlake.edu.cn/software/gcta/bin/gcta-${GCTA_VERSION}-linux-x86_64.zip"; \
    echo "${GCTA_SHA256}  gcta.zip" | sha256sum -c -; \
    unzip -q gcta.zip; \
    cd "gcta-${GCTA_VERSION}-linux-x86_64"; \
    chmod +x gcta; \
    ./gcta --appimage-extract >/dev/null; \
    mkdir -p /opt/gcta/bin /opt/gcta/lib; \
    mv squashfs-root/usr/bin/gcta64 /opt/gcta/bin/gcta64; \
    mv squashfs-root/usr/lib/*.so* /opt/gcta/lib/; \
    ln -s bin/gcta64 /opt/gcta/gcta; \
    cd /tmp; rm -rf gcta.zip "gcta-${GCTA_VERSION}-linux-x86_64"; \
    /opt/gcta/gcta 2>&1 | grep -q "version v${GCTA_VERSION}"

RUN pip install --no-cache-dir "git+https://github.com/broadinstitute/dig-bioindex.git@master"

COPY variant_sifter_pipeline /app/variant_sifter_pipeline

# Smoke test: the entrypoint module must import (boto3 arrives via bioindex;
# a Batch job that fails on import wastes a Fargate start).
RUN python -c "import boto3, variant_sifter_pipeline.run"

# Batch supplies the args:  --username <u> --dataset <d> --guid <g>
# Config comes from env: BIOINDEX_S3_BUCKET, BIOINDEX_RDS_SECRET, BIOINDEX_BIO_SCHEMA.
ENTRYPOINT ["python", "-m", "variant_sifter_pipeline.run"]
