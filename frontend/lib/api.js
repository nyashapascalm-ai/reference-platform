import { supabase } from './supabaseClient';
export const API = process.env.NEXT_PUBLIC_API_URL || '';

function humanError(data, status) {
  // FastAPI returns { detail: ... } where detail is a string, an object, or an array of validation errors.
  const d = data && typeof data === 'object' ? data.detail : data;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    // pydantic validation errors -> "Field name: message"
    return d.map((e) => {
      const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : '';
      const msg = e.msg || 'invalid value';
      const label = String(field).replace(/_/g, ' ');
      return field ? `${label}: ${msg}` : msg;
    }).join('; ');
  }
  if (d && typeof d === 'object') return d.error || JSON.stringify(d);
  return `Request failed (HTTP ${status})`;
}

export async function api(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const { data } = await supabase.auth.getSession();
    const token = data?.session?.access_token;
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`${API}${path}`, {
    method, headers, body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) throw new Error(humanError(data, res.status));
  return data;
}
