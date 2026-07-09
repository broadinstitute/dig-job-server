# Runtime for the gwas-ce-variant-sifter Batch job: builds the p-value-filtered
# associations for one uploaded GWAS and indexes them into the gwas_ce bioindex.
# Deliberately separate from the GWAS-CE app image — bioindex pins Pydantic v1,
# the app uses v2. This container does NOT import job_server.
FROM python:3.10-slim

WORKDIR /app

# git is needed to install bioindex from source (matches the deployed portal runtime).
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "git+https://github.com/broadinstitute/dig-bioindex.git@master"

COPY variant_sifter_pipeline /app/variant_sifter_pipeline

# Batch supplies the args:  --username <u> --dataset <d> --guid <g>
# Config comes from env: BIOINDEX_S3_BUCKET, BIOINDEX_RDS_SECRET, BIOINDEX_BIO_SCHEMA.
ENTRYPOINT ["python", "-m", "variant_sifter_pipeline.run"]
