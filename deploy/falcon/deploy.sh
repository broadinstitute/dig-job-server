#!/usr/bin/env bash
#
# Build the FALCON image, push it to ECR, and register its Batch job definition.
#
#   ./deploy/falcon/deploy.sh --falcon-sha <commit>                  # dataset mode
#   ./deploy/falcon/deploy.sh --falcon-sha <commit> --mode config    # research mode
#
# Run from the repository root -- the build context is the repo, filtered by
# deploy/falcon/Dockerfile.dockerignore.
#
# --falcon-sha pins the FALCON engine commit the image is built from. The engine
# lives in a separate repository, so unlike the rest of this repo its version is
# not implied by the checkout; it is an explicit, reviewable argument, and it is
# what every run's provenance is stamped with.
#
# --mode selects the job definition's parameter/command shape:
#   dataset (default) -- ["--username", "Ref::username", "--dataset", "Ref::dataset"]
#   config            -- ["Ref::s3_config"], for falcon-batch <config.ini>

set -Eeuo pipefail

ACCOUNT="${AWS_ACCOUNT_ID:-005901288866}"
REGION="${AWS_REGION:-us-east-1}"
REPO="falcon-repo"
IMAGE_TAG="falcon-rs"
VCPU="16"
MEMORY="32768"
EPHEMERAL="200"
MODE="dataset"
JOB_DEF=""
FALCON_SHA=""
FALCON_REPO="${FALCON_REPO:-https://github.com/Alex-Llamas/falcon.git}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --falcon-sha) [[ $# -ge 2 ]] || { echo "--falcon-sha requires a value" >&2; exit 2; }
                      FALCON_SHA="$2"; shift 2 ;;
        --mode)       [[ $# -ge 2 ]] || { echo "--mode requires a value" >&2; exit 2; }
                      MODE="$2"; shift 2 ;;
        --job-def)    [[ $# -ge 2 ]] || { echo "--job-def requires a value" >&2; exit 2; }
                      JOB_DEF="$2"; shift 2 ;;
        --vcpu)       [[ $# -ge 2 ]] || { echo "--vcpu requires a value" >&2; exit 2; }
                      VCPU="$2"; shift 2 ;;
        --memory)     [[ $# -ge 2 ]] || { echo "--memory requires a value" >&2; exit 2; }
                      MEMORY="$2"; shift 2 ;;
        --tag)        [[ $# -ge 2 ]] || { echo "--tag requires a value" >&2; exit 2; }
                      IMAGE_TAG="$2"; shift 2 ;;
        *) echo "unknown flag: $1" >&2; exit 2 ;;
    esac
done

[[ -n "$FALCON_SHA" ]] || { echo "--falcon-sha is required (the FALCON engine commit to build)" >&2; exit 2; }

case "$MODE" in
    dataset) PARAMS='username=,dataset='
             COMMAND='["--username", "Ref::username", "--dataset", "Ref::dataset"]'
             JOB_DEF="${JOB_DEF:-falcon-rs-dataset-job}" ;;
    config)  PARAMS='s3_config='
             COMMAND='["Ref::s3_config"]'
             JOB_DEF="${JOB_DEF:-falcon-rs-job}" ;;
    *) echo "mode must be 'config' or 'dataset', got '$MODE'" >&2; exit 2 ;;
esac

REPO_URI="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${REPO}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

[[ -d "$REPO_ROOT/deploy/falcon/reference" ]] || {
    echo "!! deploy/falcon/reference is missing; run ./deploy/falcon/fetch-reference.sh deploy/falcon/reference first" >&2
    exit 2
}

# The job role's name carries a CloudFormation-generated suffix. Look it up from
# the stack export rather than hardcoding it, so a stack rebuild does not silently
# break every deploy.
JOB_ROLE="${FALCON_JOB_ROLE:-}"
if [[ -z "$JOB_ROLE" ]]; then
    JOB_ROLE="$(aws cloudformation list-exports --region "$REGION" \
        --query "Exports[?Name=='falcon-batch-JobRoleArn'].Value" --output text 2>/dev/null || true)"
fi
[[ -n "$JOB_ROLE" && "$JOB_ROLE" != "None" ]] || {
    echo "!! could not resolve the job role ARN. Deploy the falcon-batch stack, or set FALCON_JOB_ROLE." >&2
    exit 2
}

echo "==> building ${REPO_URI}:${IMAGE_TAG} from FALCON ${FALCON_SHA}"
docker build --platform=linux/amd64 \
    --build-arg "FALCON_SHA=${FALCON_SHA}" \
    --build-arg "FALCON_REPO=${FALCON_REPO}" \
    -f "$REPO_ROOT/deploy/falcon/Dockerfile" \
    -t "${REPO_URI}:${IMAGE_TAG}" \
    "$REPO_ROOT"

echo "==> pushing to ECR"
aws ecr get-login-password --region "$REGION" \
    | docker login --username AWS --password-stdin "${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
docker push "${REPO_URI}:${IMAGE_TAG}"

DIGEST="$(aws ecr describe-images --region "$REGION" --repository-name "$REPO" \
    --image-ids "imageTag=${IMAGE_TAG}" --query 'imageDetails[0].imageDigest' --output text)"
echo "==> image digest ${DIGEST}"

echo "==> registering job definition ${JOB_DEF} (${MODE} mode, ${VCPU} vCPU / ${MEMORY} MiB)"
aws batch register-job-definition \
    --region "$REGION" \
    --job-definition-name "$JOB_DEF" \
    --type container \
    --platform-capabilities FARGATE \
    --propagate-tags \
    --tags "Project=falcon,Engine=falcon-rs,FalconSha=${FALCON_SHA},ManagedBy=deploy.sh" \
    --parameters "$PARAMS" \
    --timeout attemptDurationSeconds=86400 \
    --retry-strategy "$(cat <<'JSON'
{
  "attempts": 3,
  "evaluateOnExit": [
    {"onStatusReason": "CannotPullContainerError*", "action": "RETRY"},
    {"onStatusReason": "Task failed to start",       "action": "RETRY"},
    {"onReason": "*",                                 "action": "EXIT"}
  ]
}
JSON
)" \
    --container-properties "$(cat <<JSON
{
  "image": "${REPO_URI}@${DIGEST}",
  "command": ${COMMAND},
  "jobRoleArn": "${JOB_ROLE}",
  "executionRoleArn": "${JOB_ROLE}",
  "resourceRequirements": [
    {"type": "VCPU",   "value": "${VCPU}"},
    {"type": "MEMORY", "value": "${MEMORY}"}
  ],
  "ephemeralStorage": {"sizeInGiB": ${EPHEMERAL}},
  "networkConfiguration": {"assignPublicIp": "ENABLED"},
  "runtimePlatform": {"cpuArchitecture": "X86_64", "operatingSystemFamily": "LINUX"},
  "fargatePlatformConfiguration": {"platformVersion": "LATEST"}
}
JSON
)" \
    --query 'jobDefinitionArn' --output text

echo "==> done (FALCON ${FALCON_SHA}, ${MODE} mode)"
