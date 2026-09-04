"""Pure helpers for user-uploaded credible sets.

FastAPI-free so they unit-test without the app (mirrors job_server/variant_sifter.py):
feature logic lives here; HTTP routes stay in job_server/api.py.
"""

import csv
import gzip
import io
import math
import re
from collections import OrderedDict
from datetime import datetime

from job_server import file_utils
from job_server.variant_sifter import SIFTER_METHOD

# Tracked as a workflow_jobs `method` under the dataset's id, beside `variant-sifter`.
CREDIBLE_SETS_METHOD = "credible-sets"
# Both of these jobs ingest every attached upload, so either one's success
# after an upload means the upload is indexed.
INGEST_METHODS = (CREDIBLE_SETS_METHOD, SIFTER_METHOD)

NAME_MAX_LEN = 30
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Key-safe form of a display name: lowercase [a-z0-9-], non-empty.

    Used in S3 keys, bioindex object names and namespaced credibleSetIds, so it
    must never contain '/', ':' or ','.
    """
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    if not slug:
        raise ValueError("name must contain at least one letter or digit")
    return slug[:NAME_MAX_LEN].rstrip("-")


def validate_name(name: str) -> str:
    """The trimmed display name, or ValueError with a user-facing message."""
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")
    if len(name) > NAME_MAX_LEN:
        raise ValueError(f"name must be at most {NAME_MAX_LEN} characters")
    slugify(name)  # raises when the name has no letter or digit
    return name


def derive_status(uploaded_at: datetime, jobs: "list[dict]") -> str:
    """One of pending | indexing | indexed | failed for an upload made at
    `uploaded_at`, given the dataset's workflow_jobs rows
    ({"method", "status", "updated_at"}; other methods are ignored).

    Both timestamps come from MySQL NOW() so they compare directly.
    """
    relevant = [j for j in jobs if j["method"] in INGEST_METHODS]
    if any(j["status"] == "RUNNING" for j in relevant):
        return "indexing"
    if any(j["status"] == "SUCCEEDED" and j["updated_at"] >= uploaded_at for j in relevant):
        return "indexed"
    latest = max(relevant, key=lambda j: j["updated_at"], default=None)
    if latest and latest["status"] == "FAILED" and latest["updated_at"] >= uploaded_at:
        return "failed"
    return "pending"


def jobs_from_workflows(workflows: dict) -> "list[dict]":
    """Flatten database_utils.get_workflow_jobs_for_user's per-dataset value
    ({method: {method: {status, updated_at}}}) into derive_status's job list."""
    return [
        {"method": method, "status": inner[method]["status"], "updated_at": inner[method]["updated_at"]}
        for method, inner in workflows.items()
        if method in inner
    ]


def records_with_status(rows: "list[dict]", jobs: "list[dict]") -> "list[dict]":
    """Copy each credible_sets row and add its derived `status`."""
    return [{**row, "status": derive_status(row["uploaded_at"], jobs)} for row in rows]


# ---- file contract -------------------------------------------------------

REQUIRED_FIELDS = ("chromosome", "position", "reference", "alt",
                   "credibleSetId", "posteriorProbability")
OPTIONAL_FIELDS = ("pValue", "beta", "se", "n", "rsid")

MAX_BYTES = 20 * 1024 * 1024
MAX_ROWS = 200_000
MAX_SETS = 5_000
MAX_ERRORS = 20

_ALLELE_RE = re.compile(r"\A[ACGT]+\Z", re.IGNORECASE)
_CHROMOSOMES = {str(i) for i in range(1, 23)} | {"X", "Y", "MT"}
# Sets whose posterior probabilities sum outside this band get a warning; the
# pipeline renormalises to 1 regardless (as the aggregator does).
_PP_SUM_BAND = (0.5, 1.5)


def normalize_chromosome(value) -> "str | None":
    """'chr1' -> '1', 'M' -> 'MT'; None when not a human chromosome.

    A deliberate copy of variant_sifter_pipeline.reference.normalize_contig:
    the app must not import the pipeline package (different runtime).
    """
    c = str(value).strip().upper()
    if c.startswith("CHR"):
        c = c[3:]
    if c == "M":
        c = "MT"
    return c if c in _CHROMOSOMES else None


def _to_float(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _to_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


class _Capped:
    """A list of {line, message} that stops growing at MAX_ERRORS and reports
    how many more there were."""

    def __init__(self, noun: str):
        self.items: "list[dict]" = []
        self.overflow = 0
        self.noun = noun

    def add(self, line, message):
        if len(self.items) < MAX_ERRORS:
            self.items.append({"line": line, "message": message})
        else:
            self.overflow += 1

    def render(self) -> "list[dict]":
        if self.overflow:
            return self.items + [{"line": None, "message": f"... and {self.overflow} more {self.noun}"}]
        return self.items


def _decode(raw: bytes) -> str:
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def _row_problems(rec: dict, col_map: dict) -> "tuple[list[str], dict]":
    """Validate one canonicalised row. Returns (messages, parsed values)."""
    problems, parsed = [], {}

    chrom = normalize_chromosome(rec.get("chromosome") or "")
    if chrom is None:
        problems.append(f"chromosome {rec.get('chromosome')!r} is not one of 1-22, X, Y, MT")
    parsed["chromosome"] = chrom
    parsed["chromosome_normalised"] = chrom is not None and chrom != str(rec.get("chromosome")).strip()

    pos = _to_int(rec.get("position"))
    if pos is None or pos <= 0:
        problems.append(f"position {rec.get('position')!r} is not a positive integer")
    parsed["position"] = pos

    for field in ("reference", "alt"):
        allele = str(rec.get(field) or "")
        if not _ALLELE_RE.match(allele):
            problems.append(f"{field} {allele!r} is not an A/C/G/T string")
        parsed[field] = allele.upper()

    set_id = str(rec.get("credibleSetId") or "").strip()
    if not set_id:
        problems.append("credibleSetId is empty")
    parsed["credibleSetId"] = set_id

    pp = _to_float(rec.get("posteriorProbability"))
    if pp is None or not 0 <= pp <= 1:
        problems.append(f"posteriorProbability {rec.get('posteriorProbability')!r} is not a number in [0, 1]")
    elif pp == 0:
        problems.append("posteriorProbability must be greater than 0")
    parsed["posteriorProbability"] = pp

    if col_map.get("pValue"):
        p = _to_float(rec.get("pValue"))
        if p is None or not 0 < p <= 1:
            problems.append(f"pValue {rec.get('pValue')!r} is not a number in (0, 1]")
    if col_map.get("beta") and _to_float(rec.get("beta")) is None:
        problems.append(f"beta {rec.get('beta')!r} is not a number")
    if col_map.get("se"):
        se = _to_float(rec.get("se"))
        if se is None or se < 0:
            problems.append(f"se {rec.get('se')!r} is not a non-negative number")
    if col_map.get("n"):
        n = _to_float(rec.get("n"))
        if n is None or n <= 0:
            problems.append(f"n {rec.get('n')!r} is not a positive number")
    return problems, parsed


def validate_file(raw: bytes, filename: str, separator: "str | None", col_map: dict) -> dict:
    """Parse and validate a whole credible-set upload. Never raises for bad
    input: every problem lands in the report. `separator` None -> inferred.
    """
    errors, warnings = _Capped("errors"), _Capped("warnings")
    report = {"ok": False, "separator": separator, "row_count": 0, "set_count": 0,
              "errors": [], "warnings": [], "sets_preview": []}

    def finish():
        report["errors"] = errors.render()
        report["warnings"] = warnings.render()
        report["ok"] = not report["errors"]
        return report

    if len(raw) > MAX_BYTES:
        errors.add(None, f"File is larger than {MAX_BYTES // (1024 * 1024)} MB")
        return finish()
    missing = [f for f in REQUIRED_FIELDS if not col_map.get(f)]
    if missing:
        errors.add(None, "Required fields not mapped: " + ", ".join(missing))
        return finish()
    try:
        text = _decode(raw)
    except (OSError, EOFError, UnicodeDecodeError) as exc:
        errors.add(None, f"Could not read the file as UTF-8 text (gzip is allowed): {exc}")
        return finish()
    if not separator:
        try:
            separator = file_utils.infer_delimiter(io.StringIO(text))
        except ValueError as exc:
            errors.add(None, f"Could not detect the delimiter: {exc}")
            return finish()
    report["separator"] = separator

    reader = csv.DictReader(io.StringIO(text), delimiter=separator)
    header = reader.fieldnames or []
    absent = [col for col in col_map.values() if col not in header]
    if absent:
        errors.add(1, "Mapped columns missing from the header: " + ", ".join(absent))
        return finish()

    seen = set()
    sets: "OrderedDict[str, dict]" = OrderedDict()
    normalised_chroms = 0
    row_count = 0
    for line_no, row in enumerate(reader, start=2):
        if line_no - 1 > MAX_ROWS:
            errors.add(None, f"More than {MAX_ROWS} data rows")
            break
        rec = {field: row.get(col) for field, col in col_map.items()}
        problems, parsed = _row_problems(rec, col_map)
        if problems:
            for message in problems:
                errors.add(line_no, message)
            continue
        var_id = f'{parsed["chromosome"]}:{parsed["position"]}:{parsed["reference"]}:{parsed["alt"]}'
        key = (parsed["credibleSetId"], var_id)
        if key in seen:
            errors.add(line_no, f"duplicate variant {var_id} in set {parsed['credibleSetId']!r}")
            continue
        seen.add(key)
        entry = sets.get(parsed["credibleSetId"])
        if entry is None:
            if len(sets) >= MAX_SETS:
                errors.add(line_no, f"More than {MAX_SETS} credible sets")
                break
            entry = sets[parsed["credibleSetId"]] = {
                "variants": 0, "pp_sum": 0.0, "chromosome": parsed["chromosome"]}
        elif entry["chromosome"] != parsed["chromosome"]:
            errors.add(line_no, f"set {parsed['credibleSetId']!r} spans more than one chromosome "
                                f"({entry['chromosome']} and {parsed['chromosome']})")
            continue
        entry["variants"] += 1
        entry["pp_sum"] += parsed["posteriorProbability"]
        normalised_chroms += parsed["chromosome_normalised"]
        row_count += 1

    if row_count == 0 and not errors.items:
        errors.add(None, "No data rows found")

    for set_id, entry in sets.items():
        if not _PP_SUM_BAND[0] <= entry["pp_sum"] <= _PP_SUM_BAND[1]:
            warnings.add(None, f"set {set_id!r}: posterior probabilities sum to "
                               f"{entry['pp_sum']:.3f}; they will be renormalised to 1")
        if entry["variants"] == 1:
            warnings.add(None, f"set {set_id!r} has a single variant")
    if normalised_chroms:
        warnings.add(None, f"{normalised_chroms} chromosome values were normalised (e.g. chr1 -> 1)")

    report["row_count"] = row_count
    report["set_count"] = len(sets)
    report["sets_preview"] = [
        {"credibleSetId": set_id, "variants": e["variants"], "pp_sum": round(e["pp_sum"], 4)}
        for set_id, e in list(sets.items())[:10]
    ]
    return finish()
