import { supabase } from './supabaseClient';
export const API = process.env.NEXT_PUBLIC_API_URL || '';
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
  if (!res.ok) {
    const detail = data && typeof data === 'object' ? data.detail : data;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail || `HTTP ${res.status}`));
  }
  return data;
}
