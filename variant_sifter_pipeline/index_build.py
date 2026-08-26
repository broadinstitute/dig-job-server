"""Index the gwas-ce portal's objects in-process (same job, no separate sync Batch).

Shells out to the bioindex CLI that ships in this container. `create` upserts the
index definition (idempotent); `index` builds it. Config comes from the env the
container is launched with: BIOINDEX_S3_BUCKET, BIOINDEX_RDS_SECRET,
BIOINDEX_BIO_SCHEMA.

ONE INDEX PER DATASET. Every dataset gets its own bioindex index, MySQL table and
S3 folder rather than sharing a single `associations` table keyed by GUID. This
matters because bioindex drops the table's compound index before inserting and
rebuilds it afterwards over the WHOLE table (dig-bioindex lib/index.py). On a
shared table that means every sifter run degrades every other user's queries to a
full table scan for the duration, and build time grows with total accumulated
data rather than with the dataset being added. Per-dataset tables confine both to
the dataset being built, and make deletion a `DROP TABLE` instead of a
stale-key reindex.

The frontend must agree on the index NAME — see
`frontend/utils/sifter/associationsApi.js`, which is the single place that
composes it (`ASSOCIATIONS_INDEX_LAYOUT`).
"""

import subprocess
import sys

# The schema keeps arity 2 with the GUID still in the key even though it is now
# redundant, so the record shape, the query shape and the frontend's `q` all stay
# exactly as they were — only the index name varies between layouts.
_SCHEMA = "phenotype,chromosome:position"

# MySQL caps identifiers at 64 characters and the GUID is already 64 hex chars,
# so the physical table name uses a truncated GUID. 32 hex chars is 128 bits —
# ample against collision across the hundreds of datasets this is sized for.
_TABLE_GUID_CHARS = 32


def associations_index_name(guid: str) -> str:
    """Index name for one dataset. Must match the frontend's associationsApi.js."""
    return f"associations-{guid}"


def associations_table_name(guid: str) -> str:
    """Physical MySQL table, truncated to stay under the 64-char identifier cap."""
    return f"assoc_{guid[:_TABLE_GUID_CHARS]}"


def associations_prefix(guid: str) -> str:
    """S3 prefix bioindex ingests for this dataset. Each dataset gets a folder.

    bioindex rejects a full object key -- "S3 prefix must be a common prefix
    ending with '/'" -- so the records cannot live in a flat
    `associations/<guid>.json`. The only prefix that would match a flat object
    is `associations/`, which matches every OTHER dataset's object too, so each
    per-dataset index would ingest the whole corpus. Hence one folder each.
    """
    return f"associations/{guid}/"


def associations_key(guid: str) -> str:
    """The object `run.py` writes. MUST live under associations_prefix(guid).

    Writer and indexer agree here or the index silently builds over nothing.
    """
    return f"{associations_prefix(guid)}associations.json"


# Credible-set indexes mirror the main portal's `credible-sets` (region/locus
# query) and `credible-variants` (members of one set) definitions, per-dataset.
CREDIBLE_SETS_SCHEMA = "phenotype,chromosome:start-end"
CREDIBLE_VARIANTS_SCHEMA = "phenotype,credibleSetId"


def credible_sets_index_name(guid: str) -> str:
    return f"credible-sets-{guid}"


def credible_sets_table_name(guid: str) -> str:
    return f"credset_{guid[:_TABLE_GUID_CHARS]}"


def credible_sets_prefix(guid: str) -> str:
    return f"credible-sets/{guid}/"


def credible_sets_key(guid: str) -> str:
    return f"{credible_sets_prefix(guid)}sets.json"


def credible_variants_index_name(guid: str) -> str:
    return f"credible-variants-{guid}"


def credible_variants_table_name(guid: str) -> str:
    return f"credvar_{guid[:_TABLE_GUID_CHARS]}"


def credible_variants_prefix(guid: str) -> str:
    return f"credible-variants/{guid}/"


def credible_variants_key(guid: str) -> str:
    return f"{credible_variants_prefix(guid)}variants.json"


def _create_and_build(name: str, table: str, prefix: str, schema: str) -> None:
    base = [sys.executable, "-m", "bioindex.main"]

    # `create` logs "Failed to create index ..." and STILL EXITS 0, so check=True
    # alone lets a bad prefix or schema through; it then surfaces from the next
    # command as a misleading `KeyError: No such index`. Inspect the output.
    created = subprocess.run(
        base + ["create", name, table, prefix, schema, "--yes"],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    print(created.stdout, end="")
    if "Failed to create" in created.stdout:
        raise RuntimeError(f"bioindex create failed for {name}: {created.stdout.strip()}")

    # Not captured: this is the long step and its progress belongs in the job
    # log as it happens, not buffered until it finishes.
    subprocess.run(base + ["index", name, "--yes"], check=True)


def index_associations(guid: str) -> None:
    """Create (idempotent) then build this dataset's own associations index."""
    _create_and_build(associations_index_name(guid), associations_table_name(guid),
                      associations_prefix(guid), _SCHEMA)


def index_credible_sets(guid: str) -> None:
    _create_and_build(credible_sets_index_name(guid), credible_sets_table_name(guid),
                      credible_sets_prefix(guid), CREDIBLE_SETS_SCHEMA)


def index_credible_variants(guid: str) -> None:
    _create_and_build(credible_variants_index_name(guid),
                      credible_variants_table_name(guid),
                      credible_variants_prefix(guid), CREDIBLE_VARIANTS_SCHEMA)
