// Keep the selected profile stable in this tab, even if another tab switches.
let selectedProfile = localStorage.getItem("study-profile") || "principal";

export function profileHeaders() {
  return { "X-Study-Profile": selectedProfile };
}

export function selectProfile(id) {
  selectedProfile = id;
  localStorage.setItem("study-profile", id);
}

export async function api(path, options = {}) {
  const headers = { ...profileHeaders(), ...(options.headers || {}) };
  let body = options.body;
  if (body !== undefined && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }
  const response = await fetch(path, {
    ...options,
    headers,
    body,
    credentials: "same-origin",
  });
  const type = response.headers.get("content-type") || "";
  const result = type.includes("application/json")
    ? await response.json()
    : null;
  if (!response.ok)
    throw new Error(
      result?.error || "Não foi possível concluir a solicitação.",
    );
  return result;
}
