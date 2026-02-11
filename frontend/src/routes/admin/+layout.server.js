import { env } from '$env/dynamic/private';

const API = env.INTERNAL_API_URL || 'http://localhost:8000';

export async function load({ fetch, url }) {
  // Server-side auth check: forward the request cookies to the Flask backend
  try {
    const res = await fetch(`${API}/api/auth/me`);
    const data = await res.json();
    return { serverAuthenticated: data.authenticated === true };
  } catch {
    return { serverAuthenticated: false };
  }
}
