// GWAS-Hub demo mode: /gwas-hub?mode=demo shows the hub landing page without
// a membership check, with the pipeline cards rendered non-clickable. The
// flag lives only in the query string, so following any link drops it and
// the normal gate applies again.

export const HUB_DEMO_QUERY_KEY = "mode";
export const HUB_DEMO_QUERY_VALUE = "demo";

export const isHubDemo = (query) =>
    query?.[HUB_DEMO_QUERY_KEY] === HUB_DEMO_QUERY_VALUE;
