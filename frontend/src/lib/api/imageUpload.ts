import { apiFetch } from '@/lib/api/unauthorized';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
export const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
export const IMAGE_ACCEPT = ALLOWED_IMAGE_TYPES.join(',');
const MAX_SIZE = 5 * 1024 * 1024; // 5MB — matches backend

/**
 * A stored upload URL as an `<img src>`. Local storage writes `/uploads/...`,
 * which the API serves, so it resolves against the API origin, not this page's
 * (#941). Cloud URLs are absolute and pass through.
 */
export function uploadUrl(url: string | null | undefined): string | undefined {
  if (!url) return undefined;
  // `//host/x` is protocol-relative, another origin, not a local path.
  return url.startsWith('/') && !url.startsWith('//') ? new URL(url, API_BASE_URL).href : url;
}

/** Why `file` cannot be uploaded as an image, or null when it can. */
export function imageFileProblem(file: File): { title: string; description: string } | null {
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    return { title: 'Invalid file', description: 'Use JPEG, PNG, WebP, or GIF.' };
  }
  if (file.size > MAX_SIZE) {
    return { title: 'File too large', description: 'Maximum size is 5MB.' };
  }
  return null;
}

/**
 * FastAPI's `detail` is polymorphic: a string for HTTPException, but an array
 * of {loc, msg, type} for 422 validation errors. Interpolating the array gives
 * "[object Object]" (#215), so pull out the msg fields.
 */
function extractDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail || null;
  if (Array.isArray(detail)) {
    const msgs = detail.map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : null)).filter(Boolean);
    return msgs.length ? msgs.join('; ') : null;
  }
  if (detail && typeof detail === 'object' && 'msg' in detail) return String((detail as { msg: unknown }).msg);
  return null;
}

/**
 * POST `file` as multipart form-data to `path` under the API (raw fetch so the
 * browser sets the boundary; cookie-authenticated). Resolves to the JSON body;
 * throws an Error carrying the server's message (429 and 4xx included).
 */
export async function uploadImage<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await apiFetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    credentials: 'include',
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(extractDetail(body?.detail) || 'Upload failed');
  }
  return res.json();
}
