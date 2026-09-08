// Decision logic for ColumnMappingTable.vue, kept pure so it is unit-testable
// without mounting PrimeVue.

/** A field may be picked by at most one column; the column's own pick stays enabled. */
export function isOptionDisabled(selectedFields, optionValue, column) {
  const claimedElsewhere = Object.entries(selectedFields || {}).some(
    ([col, field]) => field === optionValue && col !== column,
  );
  return claimedElsewhere;
}

export function resetMapping(columns) {
  return Object.fromEntries((columns || []).map((column) => [column, null]));
}

export function withField(selectedFields, column, value) {
  return { ...(selectedFields || {}), [column]: value ?? null };
}
