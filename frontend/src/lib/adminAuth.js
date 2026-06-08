// Admin Portal auth helpers — HTTP Basic Auth via sessionStorage.
const KEY = "pnc_admin_basic_v1";

export function getAuthHeader() {
  try {
    const tok = sessionStorage.getItem(KEY);
    return tok ? { Authorization: `Basic ${tok}` } : {};
  } catch {
    return {};
  }
}

export function setCreds(username, password) {
  const token = btoa(`${username}:${password}`);
  sessionStorage.setItem(KEY, token);
}

export function clearCreds() {
  sessionStorage.removeItem(KEY);
}

export function hasCreds() {
  return !!sessionStorage.getItem(KEY);
}

const API = process.env.REACT_APP_BACKEND_URL || "";

export async function adminFetch(path, init = {}) {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      ...(init.headers || {}),
      ...getAuthHeader(),
    },
  });
  if (res.status === 401) {
    clearCreds();
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${txt}`);
  }
  return res;
}

export function buildCsvUrl(filters = {}) {
  const u = new URL(`${API}/api/admin/employees.csv`);
  for (const [k, v] of Object.entries(filters)) {
    if (v) u.searchParams.set(k, v);
  }
  return u.toString();
}

export async function downloadCsv(filters = {}) {
  // Inject Basic auth into the request itself (the URL can't carry it for
  // every browser); then turn the response into a Blob download.
  const u = new URL(buildCsvUrl(filters));
  const res = await adminFetch(u.pathname + u.search);
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  // server already sets Content-Disposition; we still set a friendly name
  a.download = `pnc-employees-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
}
