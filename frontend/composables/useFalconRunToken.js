// frontend/composables/useFalconRunToken.js
// Mints a short-lived FALCON run token. The CLI installer (run.sh) trades
// this token for the per-run config + presigned upload URLs server-side.
export async function fetchFalconRunToken(datasetName) {
  // Match the rest of the app (useAxios.js): hit the API base URL and
  // authenticate with the Bearer token from localStorage. The previous
  // relative URL hit the Nuxt server, and credentials:"include" sent cookies
  // this API does not use, so the call 404'd/401'd in local dev.
  const config = useRuntimeConfig();
  const token = localStorage.getItem("authToken");
  const res = await fetch(`${config.public.apiBaseUrl}/api/falcon/run-token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ dataset_name: datasetName }),
  });
  if (!res.ok) throw new Error(`run-token: HTTP ${res.status}`);
  return res.json(); // { token, expires_at }
}
