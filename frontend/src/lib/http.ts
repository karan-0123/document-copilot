import { supabase } from './supabase';
import { env } from './env';

export class APIError extends Error {
  status: number;
  detail: string;

  constructor(status: number, message: string, detail: string) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.detail = detail;
  }
}

export async function request(path: string, options: RequestInit = {}): Promise<Response> {
  const url = `${env.VITE_API_BASE_URL}${path}`;

  // Dynamically retrieve the active user session token to ensure it is fresh
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  const headers = new Headers(options.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let detail = 'An unexpected error occurred';
      try {
        const errorData = await res.json();
        detail = errorData.detail || detail;
      } catch {
        // Fallback to text response if JSON parsing fails
      }
      throw new APIError(res.status, res.statusText, detail);
    }

    return res;
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(500, 'Network Error', error instanceof Error ? error.message : 'Network request failed');
  }
}
