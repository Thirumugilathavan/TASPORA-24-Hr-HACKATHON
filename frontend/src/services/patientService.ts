import { config } from '../lib/config';
import { MOCK_PATIENT, MOCK_VILLAGES } from '../mocks/data';
import { CreatePatientRequest, PageResponse } from '../types/api';
import { Patient, Village } from '../types/index';
import { apiRequest } from './apiClient';

export const patientService = {
  async getVillages(): Promise<Village[]> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 150));
      return MOCK_VILLAGES;
    }

    try {
      const res = await apiRequest<PageResponse<Village> | Village[]>('/api/villages');
      if (Array.isArray(res)) return res;
      return res.items || [];
    } catch (err) {
      console.warn('Backend /api/villages unavailable, falling back to cached villages:', err);
      return MOCK_VILLAGES;
    }
  },

  async getPatient(idOrUserId: string): Promise<Patient> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 150));
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

    return await apiRequest<Patient>(`/api/patients/${idOrUserId}`);
  },

  async createPatient(payload: CreatePatientRequest): Promise<Patient> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 350));
      const village = MOCK_VILLAGES.find((v) => v.id === payload.village_id) || MOCK_VILLAGES[0];
      const newPatient: Patient = {
        id: `pat-${Date.now().toString().slice(-4)}`,
        user_id: `user-${Date.now().toString().slice(-4)}`,
        village_id: payload.village_id,
        village,
        date_of_birth: payload.date_of_birth,
        preferred_language: payload.preferred_language,
        consent_given: payload.consent_given ?? false,
        emergency_contact_phone: payload.emergency_contact_phone,
        created_at: new Date().toISOString(),
      };
      localStorage.setItem('carebridge_patient', JSON.stringify(newPatient));
      return newPatient;
    }

    return await apiRequest<Patient>('/api/patients', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
