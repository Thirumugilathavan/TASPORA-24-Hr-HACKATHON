// Centralized frontend configuration for NALAM

const envMock = import.meta.env?.VITE_MOCK_MODE;
const defaultMockMode = envMock === 'true';

// Allow runtime override via localStorage for demo flexibility
const storedMockOverride = typeof window !== 'undefined'
  ? (localStorage.getItem('nalam_mock_mode') || localStorage.getItem('carebridge_mock_mode'))
  : null;

/**
 * Determine API base URL:
 * - In any deployed browser environment (hostname !== 'localhost' and !== '127.0.0.1'):
 *   ALWAYS return "" (empty string, same-origin relative routing).
 *   This guarantees that requests like /api/auth/login route via Vercel reverse proxy to the deployed backend.
 * - In local development (localhost / 127.0.0.1):
 *   Use VITE_API_BASE_URL if explicitly configured, otherwise fallback to 'http://localhost:8000'.
 */
const getApiBaseUrl = (): string => {
  // 1. Production browser runtime guard: if running on a live domain, NEVER call localhost
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '0.0.0.0';
    if (!isLocalhost) {
      return '';
    }
  }

  // 2. Explicit environment variable
  if (import.meta.env?.VITE_API_BASE_URL !== undefined && import.meta.env.VITE_API_BASE_URL !== '') {
    return import.meta.env.VITE_API_BASE_URL;
  }

  // 3. Fallback for build / local dev
  return import.meta.env?.PROD ? '' : 'http://localhost:8000';
};

export const config = {
  apiBaseUrl: getApiBaseUrl(),
  isMockMode: storedMockOverride !== null ? storedMockOverride === 'true' : defaultMockMode,
  setMockMode: (enabled: boolean) => {
    localStorage.setItem('nalam_mock_mode', enabled ? 'true' : 'false');
    localStorage.setItem('carebridge_mock_mode', enabled ? 'true' : 'false');
    window.location.reload();
  },
};

export const toggleMockMode = (enabled: boolean) => {
  config.setMockMode(enabled);
};

