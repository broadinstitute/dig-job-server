# FALCON as a job-server method

Runs FALCON on AWS Batch against a dig-job-server dataset, writing results and a
manifest the server's own `job_server.falcon.validate_manifest` accepts.

```
falcon_prep/                 the converter (upload -> FALCON sumstats), importable + tested
deploy/falcon/
  Dockerfile                 builds the engine from a pinned FALCON commit
  Dockerfile.dockerignore    scoped build context (BuildKit prefers this over the root file)
  falcon-batch.sh            container entrypoint: stage, convert, run, upload, attest
  deploy.sh                  build -> ECR -> register job definition
  fetch-reference.sh         pulls the 301 MB bundled reference into the build context
  configs/                   the config template dataset mode renders
  tests/                     image, entrypoint and end-to-end shell suites
deploy/cloudformation/falcon-batch.yaml
```

## Why the engine is cloned rather than vendored

FALCON itself lives in a separate repository. The builder clones it at the
commit given by `--falcon-sha`, so the engine version is an explicit,
reviewable pin instead of whatever happened to be checked out, and that commit
is what each run's provenance is stamped with.

## Why `job_server/falcon.py` is copied into the image

`falcon_prep/manifest.py` imports `SCHEMA_VERSION` from it rather than
redeclaring it. The two previously lived in different repositories with nothing
enforcing agreement — a producer and validator that can drift eventually will.
That module is stdlib-only, so carrying it costs nothing.
`test_manifest.py::test_schema_version_is_the_validators_own_constant` locks it.

## Usage

```bash
./deploy/falcon/fetch-reference.sh deploy/falcon/reference   # once; 301 MB
./deploy/falcon/deploy.sh --falcon-sha <commit>

aws batch submit-job --region us-east-1 \
  --job-name falcon-<dataset> \
  --job-queue falcon-queue \
  --job-definition falcon-rs-dataset-job \
  --parameters "username=<user>,dataset=<dataset>"
```

`deploy.sh` resolves the job role from the `falcon-batch-JobRoleArn` stack
export, so a stack rebuild does not silently break deploys. Override with
`FALCON_JOB_ROLE` if needed.

## Scope

EUR datasets only — FALCON's LD reference is EUR and LD structure is
ancestry-specific, so other ancestries are rejected rather than run with a
warning. GRCh37, or GRCh38 when the upload carries an rsID column; GRCh38
without rsIDs fails loudly, as no GRCh38 dbSNP map is available yet.
