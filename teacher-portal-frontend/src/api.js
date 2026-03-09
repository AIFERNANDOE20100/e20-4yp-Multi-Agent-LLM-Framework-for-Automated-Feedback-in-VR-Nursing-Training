const API_BASE_URL = "http://localhost:8001";

export async function apiGet(path) {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function apiPost(path, body, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  return res.json();
}

export async function apiUpload(path, formData) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  return res.json();
}
