#!/usr/bin/env bash
# Pull the small, slow-changing FALCON reference data into the build context so
# it can be baked into the image. The LD reference is deliberately NOT included:
# at 39 GB it is larger than any sensible image, and Fargate re-pulls images per
# task, so bundling it would be slower than the runtime s5cmd download.
set -Eeuo pipefail
DEST="${1:-reference}"
mkdir -p "$DEST"
for p in genes V2G annotations; do
    echo "==> fetching $p"
    aws s3 cp --quiet --recursive "s3://falcon-data-center/$p/" "$DEST/$p/"
done
du -sh "$DEST"
