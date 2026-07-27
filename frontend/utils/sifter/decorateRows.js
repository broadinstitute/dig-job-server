import { ASSOCIATIONS_TABLE_FORMAT } from "./associationsTableFormat.js";

// Upstream runs ASSOCIATIONS_TABLE_FORMAT["data convert"] through the portal's
// generic 668-line dataConvert engine. Only four rule types appear in this
// mapping, so we interpret those four rather than vendoring the engine. The
// MAPPING is verbatim upstream; only this interpreter is ours.
//
// Semantics verified against dig-dug-portal@5619cbfe1 src/utils/dataConvert.js
// by running its actual convertData() (not just reading it):
//   raw        - assigns when the source value is truthy, EXCEPT that an
//                exact numeric 0 is special-cased to the string "0" first
//                (`if (d[field] === 0) rawValue = "0"`) and "0" *is* truthy,
//                so it gets assigned too. Only null/undefined/""/false/NaN
//                are actually dropped. Confirmed empirically: feeding
//                `{ beta: 0 }` through upstream's real convertData() yields
//                `Beta: "0"`, not an omitted field.
//   join       - fields joined by a single separator
//   join multi - fields joined by a per-position separator array
//   calculate  - only "-log10" is used: -Math.log10(value), assigned unguarded

function joinValues(fields, joinBy, row) {
  return fields.map((f) => row[f]).join(joinBy);
}

function joinMultiValues(fields, joinBy, row) {
  let out = "";
  for (let i = 0; i < fields.length; i++) {
    out += row[fields[i]];
    if (i < fields.length - 1) out += joinBy[i];
  }
  return out;
}

function deriveZScore(decorated, raw) {
  const existing = decorated["Z Score"];
  if (existing != null && existing !== "") return existing;

  const beta = decorated.Beta ?? raw.beta;
  const stdErr = decorated["Standard Error"] ?? raw.stdErr;
  if (
    typeof beta === "number" &&
    typeof stdErr === "number" &&
    stdErr !== 0 &&
    !Number.isNaN(beta) &&
    !Number.isNaN(stdErr)
  ) {
    return beta / stdErr;
  }
  return existing;
}

export function decorateAssociationRows(rawRows) {
  if (!Array.isArray(rawRows) || !rawRows.length) return [];
  const rules = ASSOCIATIONS_TABLE_FORMAT["data convert"];

  return rawRows.map((raw) => {
    const row = { ...raw };
    for (const rule of rules) {
      const name = rule["field name"];
      switch (rule.type) {
        case "raw": {
          const source = row[rule["raw field"]];
          const value = source === 0 ? "0" : source;
          if (value) row[name] = value;
          break;
        }
        case "join":
          row[name] = joinValues(rule["fields to join"], rule["join by"], row);
          break;
        case "join multi":
          row[name] = joinMultiValues(rule["fields to join"], rule["join by"], row);
          break;
        case "calculate":
          if (rule["calculation type"] === "-log10") {
            row[name] = -Math.log10(row[rule["raw field"]]);
          }
          break;
        default:
          break;
      }
    }
    const zScore = deriveZScore(row, raw);
    if (zScore != null && zScore !== "") row["Z Score"] = zScore;
    return row;
  });
}
