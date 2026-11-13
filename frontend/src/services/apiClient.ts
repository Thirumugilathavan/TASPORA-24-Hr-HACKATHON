import { config } from '../lib/config';

export class ApiConnectionError extends Error {
  constructor(message: string, public status?: number, public code?: string) {
    super(message);
    this.name = 'ApiConnectionError';
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${config.apiBaseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const token = typeof window !== 'undefined' ? (localStorage.getItem('nalam_token') || localStorage.getItem('carebridge_token')) : null;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = null;
      }

      // Handle expired / invalid token — clear credentials and signal the app
      // CRITICAL: NEVER fire session-expired on auth endpoints (/auth/login or /auth/register)!
      // A 401 on /auth/login is "invalid phone/password", NOT an expired session!
      const isAuthEndpoint = endpoint.includes('/auth/login') || endpoint.includes('/auth/register');
      if (response.status === 401 && !isAuthEndpoint) {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('nalam_token');
          localStorage.removeItem('carebridge_token');
          localStorage.removeItem('nalam_user');
          localStorage.removeItem('carebridge_user');
          localStorage.removeItem('nalam_patient');
          localStorage.removeItem('carebridge_patient');
          localStorage.removeItem('carebridge_my_request_ids');
          window.dispatchEvent(new CustomEvent('nalam:session-expired'));
        }
      }

      const errorCode =
        errorData?.error?.code ||
        errorData?.detail?.error?.code ||
        `HTTP_${response.status}`;

      const errorMessage =
        errorData?.error?.message ||
        errorData?.detail?.error?.message ||
        (typeof errorData?.detail === 'string' ? errorData.detail : null) ||
        (Array.isArray(errorData?.detail) ? errorData.detail.map((e: any) => e.msg || e.message).join(', ') : null) ||
        `Request failed with status ${response.status} (${response.statusText})`;

      throw new ApiConnectionError(errorMessage, response.status, errorCode);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (err: unknown) {
    if (err instanceof ApiConnectionError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : 'Network error or backend server unavailable';
    const targetDisplay = config.apiBaseUrl || (typeof window !== 'undefined' ? `${window.location.origin}/api` : '/api');
    throw new ApiConnectionError(
      `Unable to connect to NALAM AI API at ${targetDisplay}. Please verify the backend is running. (${message})`,
      0,
      'NETWORK_ERROR'
    );
  }
}
