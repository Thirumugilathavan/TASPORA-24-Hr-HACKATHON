// Centralized frontend configuration for NALAM

const envMock = import.meta.env?.VITE_MOCK_MODE;
const defaultMockMode = envMock === 'true';

// Allow runtime override via localStorage for demo flexibility
const storedMockOverride = typeof window !== 'undefined' ? localStorage.getItem('carebridge_mock_mode') : null;

// Determine API base URL:
// In production: default to "" (empty string) for same-origin relative requests (/api/...) under single Vercel domain
// In development: default to 'http://localhost:8000' (or VITE_API_BASE_URL if explicitly configured)
const getApiBaseUrl = (): string => {
  if (import.meta.env?.VITE_API_BASE_URL !== undefined) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  return import.meta.env?.PROD ? '' : 'http://localhost:8000';
};

export const config = {
  apiBaseUrl: getApiBaseUrl(),
  isMockMode: storedMockOverride !== null ? storedMockOverride === 'true' : defaultMockMode,
  setMockMode: (enabled: boolean) => {
    localStorage.setItem('carebridge_mock_mode', enabled ? 'true' : 'false');
    window.location.reload();
  },
};

export const toggleMockMode = (enabled: boolean) => {
  config.setMockMode(enabled);
};
