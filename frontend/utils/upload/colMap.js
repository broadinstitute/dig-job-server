// The upload UIs keep {column: canonicalField|null} while the user maps; the
// backend wants {canonicalField: column}. One transposition for both forms.
export function selectedFieldsToColMap(selectedFields) {
  return Object.fromEntries(
    Object.entries(selectedFields || {})
      .filter(([, field]) => field !== null && field !== undefined)
      .map(([column, field]) => [field, column]),
  );
}
