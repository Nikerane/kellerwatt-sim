// Leak-scan core (B6). The public bundle must never carry confidential business
// inputs. NOTE (flagged for confirmation): the validated ceilings 61.1/68.3/77.3
// are PUBLIC, market-derived figures and ARE the honest finding the page shows, so
// they are intentionally NOT forbidden — only genuinely-confidential inputs are.
export const FORBIDDEN = [
  "capex_eur",
  "real_fee_rate",
  "term_sheet",
  "params_real",
  "dist/real",
];

/** Return the forbidden tokens present in `text` (empty array = clean). */
export function findLeaks(text, forbidden = FORBIDDEN) {
  return forbidden.filter((token) => text.includes(token));
}

/** Structural checks on the sanitized results doc: no real IRR/payback may leak. */
export function checkSanitizedDoc(doc) {
  const issues = [];
  for (const sc of doc.scenarios ?? []) {
    if (sc.irr?.value !== null && sc.irr?.value !== undefined) {
      issues.push(`scenario ${sc.id}: irr.value must be null in the public bundle (got ${sc.irr.value})`);
    }
    if (sc.payback_years?.value !== null && sc.payback_years?.value !== undefined) {
      issues.push(`scenario ${sc.id}: payback_years.value must be null in the public bundle`);
    }
  }
  return issues;
}
