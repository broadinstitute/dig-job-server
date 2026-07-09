"""Index the gwas-ce portal's objects in-process (same job, no separate sync Batch).

Shells out to the bioindex CLI that ships in this container. `create` upserts the
index definition (idempotent); `index` builds incrementally — only new
`<guid>.json` objects under the prefix are read. Config comes from the env the
container is launched with: BIOINDEX_S3_BUCKET, BIOINDEX_RDS_SECRET,
BIOINDEX_BIO_SCHEMA.
"""

import subprocess
import sys

# Must match dig-bioindex-configs/portals/gwas-ce.yaml.
_ASSOCIATIONS = ("associations", "associations", "associations/",
                 "phenotype,chromosome:position")


def index_associations() -> None:
    """Create (idempotent) then incrementally build the `associations` index."""
    name, table, prefix, schema = _ASSOCIATIONS
    base = [sys.executable, "-m", "bioindex.main"]
    subprocess.run(base + ["create", name, table, prefix, schema, "--yes"], check=True)
    subprocess.run(base + ["index", name, "--yes"], check=True)
