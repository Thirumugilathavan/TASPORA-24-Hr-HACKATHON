import { config } from '../lib/config';
import { MOCK_PATIENT, MOCK_USER, MOCK_VILLAGES } from '../mocks/data';
import { LoginRequest, LoginResponse, PageResponse, RegisterRequest, RegisterResponse } from '../types/api';
import { Patient, User, Village } from '../types/index';
import { apiRequest } from './apiClient';

export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    if (config.isMockMode) {
      // Simulate network latency in mock mode
      await new Promise((r) => setTimeout(r, 400));
      if (credentials.phone.length < 10) {
        throw new Error('Please enter a valid 10-digit mobile number.');
      }
      const response: LoginResponse = {
        access_token: 'mock-jwt-token-demo-mode-12345',
        token_type: 'bearer',
        role: 'PATIENT',
        user_id: MOCK_USER.id,
      };
      localStorage.setItem('carebridge_token', response.access_token);
      localStorage.setItem('carebridge_user', JSON.stringify(MOCK_USER));
      localStorage.setItem('carebridge_patient', JSON.stringify(MOCK_PATIENT));
      return response;
    }

    const res = await apiRequest<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    localStorage.setItem('carebridge_token', res.access_token);
    return res;
  },

  async register(data: RegisterRequest): Promise<RegisterResponse> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 500));
      const newUser: User = {
        id: `mock-user-${Date.now()}`,
        name: data.name,
        phone: data.phone,
        role: 'PATIENT',
        created_at: new Date().toISOString(),
      };
      localStorage.setItem('carebridge_user', JSON.stringify(newUser));
      return {
        id: newUser.id,
        name: newUser.name,
        phone: newUser.phone,
        role: 'PATIENT',
        created_at: newUser.created_at,
      };
    }

    return await apiRequest<RegisterResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        name: data.name,
        phone: data.phone,
        password: data.password,
        role: 'PATIENT', // Contract: public self-registration enforces PATIENT
      }),
    });
  },

  async getVillages(): Promise<Village[]> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 150));
      return MOCK_VILLAGES;
    }

    const res = await apiRequest<PageResponse<Village>>('/api/villages');
    return res.items || [];
  },

  async getCurrentPatient(patientId?: string): Promise<Patient> {
    if (config.isMockMode) {
      const stored = localStorage.getItem('carebridge_patient');
      if (stored) {
        try {
          return JSON.parse(stored);
        } catch {
          // fallback
        }
      }
      return MOCK_PATIENT;
    }

    return await apiRequest<Patient>(`/api/patients/${patientId}`);
  },

  logout(): void {
    localStorage.removeItem('carebridge_token');
    localStorage.removeItem('carebridge_user');
    localStorage.removeItem('carebridge_patient');
  },
};
