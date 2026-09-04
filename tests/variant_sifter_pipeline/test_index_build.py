"""Naming rules for the per-dataset associations index.

These are all constraints imposed from outside this repo -- by bioindex, by
MySQL, and by the frontend -- so none of them are visible in the code that
depends on them. Each test below records one that has already broken or could.
"""

from variant_sifter_pipeline import index_build

GUID = "f83b34c11a4c412b6176334969cbd2dae7dba2a2aee8e1b9a9b91625c1790e34"


def test_prefix_is_a_directory_style_common_prefix():
    """bioindex rejects a full object key with 'S3 prefix must be a common
    prefix ending with /'. It logs that and still exits 0, so a regression here
    surfaces as a confusing 'No such index' from the following index build."""
    assert index_build.associations_prefix(GUID).endswith("/")


def test_written_key_lives_under_the_indexed_prefix():
    """The writer/indexer invariant. Break it and the index builds successfully
    over zero objects -- no error anywhere, just an empty sifter."""
    key = index_build.associations_key(GUID)
    prefix = index_build.associations_prefix(GUID)
    assert key.startswith(prefix)
    assert key != prefix


def test_one_datasets_prefix_never_matches_another():
    """S3 prefixes match by string, so without the trailing slash the folder for
    guid 'aaa' would also ingest guid 'aaabbb' -- one dataset silently serving
    another user's associations."""
    a = index_build.associations_prefix("aaa")
    b = index_build.associations_prefix("aaabbb")
    assert not b.startswith(a)
    assert not a.startswith(b)


def test_table_name_fits_mysqls_64_char_identifier_cap():
    """GUIDs are already 64 hex chars, so the table name must truncate."""
    assert len(index_build.associations_table_name("f" * 64)) <= 64


def test_table_name_discriminates_on_the_leading_32_guid_chars():
    """Truncation means only the first 32 chars separate two datasets' tables.
    That is 128 bits of a random GUID, so collision is not a practical concern
    -- but it does mean GUIDs must stay random rather than becoming a prefixed
    or sequential scheme, which would collide immediately."""
    assert index_build.associations_table_name("a" * 64) == "assoc_" + "a" * 32
    assert index_build.associations_table_name(
        "a" * 64
    ) == index_build.associations_table_name("a" * 32 + "z" * 32)


def test_index_name_matches_what_the_frontend_composes():
    """frontend/utils/sifter/associationsApi.js builds `associations-<guid>`.
    The two are joined only by this string; they must be changed together."""
    assert index_build.associations_index_name(GUID) == f"associations-{GUID}"


# --- credible-set indexes: same constraints, two more index families ------


def test_credible_index_names_follow_the_portal_convention():
    """The main portal serves `credible-sets` / `credible-variants`; the
    per-dataset flavors append the GUID exactly like associations does."""
    assert index_build.credible_sets_index_name(GUID) == f"credible-sets-{GUID}"
    assert index_build.credible_variants_index_name(GUID) == f"credible-variants-{GUID}"


def test_credible_table_names_fit_mysql_and_stay_distinct():
    """Same 64-char identifier cap; the two families and associations must
    never collide with each other for the same GUID."""
    names = {index_build.associations_table_name(GUID),
             index_build.credible_sets_table_name(GUID),
             index_build.credible_variants_table_name(GUID)}
    assert len(names) == 3
    assert all(len(n) <= 64 for n in names)


def test_credible_written_keys_live_under_their_indexed_prefixes():
    """The writer/indexer invariant again, per family — and the families must
    not shadow each other's prefixes (`credible-sets/` vs `credible-variants/`
    differ, but a rename could silently cross-ingest)."""
    for prefix_fn, key_fn in [
        (index_build.credible_sets_prefix, index_build.credible_sets_key),
        (index_build.credible_variants_prefix, index_build.credible_variants_key),
    ]:
        prefix, key = prefix_fn(GUID), key_fn(GUID)
        assert prefix.endswith("/")
        assert key.startswith(prefix)
        assert key != prefix
    assert not index_build.credible_variants_prefix(GUID).startswith(
        index_build.credible_sets_prefix(GUID))


def test_credible_prefixes_never_match_another_dataset():
    for prefix_fn in (index_build.credible_sets_prefix,
                      index_build.credible_variants_prefix):
        a, b = prefix_fn("aaa"), prefix_fn("aaabbb")
        assert not b.startswith(a)
        assert not a.startswith(b)


def test_credible_schemas_match_the_main_portal():
    """The frontend queries these shapes: sets by region (locus query), the
    set's variants by id. They mirror bioindex's main-portal definitions."""
    assert index_build.CREDIBLE_SETS_SCHEMA == "phenotype,chromosome:start-end"
    assert index_build.CREDIBLE_VARIANTS_SCHEMA == "phenotype,credibleSetId"


# ---- uploaded credible sets live beside the derived objects ----------------

def test_upload_objects_live_under_the_credible_set_prefixes():
    """bioindex ingests everything under the prefix, so one per-dataset index
    serves derived + uploaded sets with no new index definitions."""
    assert index_build.upload_sets_key(GUID, "susie-v1") == \
        index_build.credible_sets_prefix(GUID) + "upload-susie-v1.json"
    assert index_build.upload_variants_key(GUID, "susie-v1") == \
        index_build.credible_variants_prefix(GUID) + "upload-susie-v1.json"


def test_upload_slug_is_recoverable_from_the_key_and_derived_objects_are_not_uploads():
    assert index_build.upload_slug_of_key(index_build.upload_sets_key(GUID, "susie-v1")) == "susie-v1"
    assert index_build.upload_slug_of_key(index_build.credible_sets_key(GUID)) is None
    assert index_build.upload_slug_of_key(index_build.credible_variants_key(GUID)) is None
