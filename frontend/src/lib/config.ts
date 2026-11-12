// Centralized frontend configuration

const envMock = import.meta.env?.VITE_MOCK_MODE;
const defaultMockMode = envMock === 'true';

// Allow runtime override via localStorage for demo flexibility
const storedMockOverride = typeof window !== 'undefined' ? localStorage.getItem('carebridge_mock_mode') : null;

export const config = {
  apiBaseUrl: import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000',
  isMockMode: storedMockOverride !== null ? storedMockOverride === 'true' : defaultMockMode,
  setMockMode: (enabled: boolean) => {
    localStorage.setItem('carebridge_mock_mode', enabled ? 'true' : 'false');
    window.location.reload();
  },
};

export const toggleMockMode = (enabled: boolean) => {
  config.setMockMode(enabled);
};
