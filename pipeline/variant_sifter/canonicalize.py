"""Rename an upload's columns to canonical field names via the dataset col_map."""


def canonicalize(row: dict, col_map: dict) -> dict:
    """Map one upload row to canonical field names.

    col_map is {canonical_field: upload_column_name} (the format produced by the
    upload UI and consumed by job_server.falcon.col_map_to_sumstats_columns).
    Only mapped fields present in the row are kept; everything else is dropped.
    """
    out = {}
    for canonical, upload_col in col_map.items():
        if upload_col in row:
            out[canonical] = row[upload_col]
    return out
