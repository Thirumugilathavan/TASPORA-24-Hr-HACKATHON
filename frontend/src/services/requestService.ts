import { config } from '../lib/config';
import { MOCK_REQUESTS } from '../mocks/data';
import { CreateRequestPayload } from '../types/api';
import { HealthcareRequest, RecommendationItem } from '../types/index';
import { apiRequest } from './apiClient';
import { recommendationService } from './recommendationService';

// Runtime in-memory storage for mock mode interactivity
let mockRequestsState = [...MOCK_REQUESTS];

function getStoredRequestIds(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem('carebridge_my_request_ids');
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveRequestId(id: string) {
  if (typeof window === 'undefined') return;
  try {
    const ids = getStoredRequestIds();
    if (!ids.includes(id)) {
      ids.unshift(id);
      localStorage.setItem('carebridge_my_request_ids', JSON.stringify(ids.slice(0, 50)));
    }
  } catch {
    // Ignore storage errors
  }
}

export const requestService = {
  async getRequests(patientId?: string, campId?: string): Promise<HealthcareRequest[]> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 200));
      let filtered = [...mockRequestsState];
      if (patientId) filtered = filtered.filter((r) => r.patient_id === patientId);
      if (campId) filtered = filtered.filter((r) => r.camp_id === campId);
      return filtered;
    }

    // 1. Try querying backend /api/requests directly for live persistent data
    try {
      const params = new URLSearchParams();
      if (patientId) params.append('patient_id', patientId);
      if (campId) params.append('camp_id', campId);
      const query = params.toString() ? `?${params.toString()}` : '';
      const serverRequests = await apiRequest<HealthcareRequest[]>(`/api/requests${query}`);
      if (Array.isArray(serverRequests)) {
        serverRequests.forEach((r) => saveRequestId(r.id));
        return serverRequests;
      }
    } catch (err) {
      console.warn('Backend list /api/requests unavailable, falling back to cached request IDs:', err);
    }

    // 2. Fallback to cached request IDs if endpoint failed
    const ids = getStoredRequestIds();
    if (ids.length === 0) {
      return [];
    }

    const requests: HealthcareRequest[] = [];
    for (const id of ids) {
      try {
        const req = await this.getRequestById(id);
        if (
          req &&
          (!patientId || req.patient_id === patientId) &&
          (!campId || req.camp_id === campId)
        ) {
          if (!req.recommendations || req.recommendations.length === 0) {
            try {
              req.recommendations = await recommendationService.getRecommendations(id);
            } catch {
              // No recommendations yet
            }
          }
          requests.push(req);
        }
      } catch (err) {
        console.warn(`Request ${id} could not be retrieved:`, err);
      }
    }
    return requests;
  },

  async getRequestsByCampId(campId: string): Promise<HealthcareRequest[]> {
    return this.getRequests(undefined, campId);
  },

  async getRequestById(id: string): Promise<HealthcareRequest> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 150));
      const found = mockRequestsState.find((r) => r.id === id);
      if (!found) throw new Error('Healthcare request not found.');
      return found;
    }

    const reqData = await apiRequest<HealthcareRequest>(`/api/requests/${id}`);
    try {
      const recs = await recommendationService.getRecommendations(id);
      reqData.recommendations = recs;
    } catch {
      // Recommendations not yet generated
    }
    return reqData;
  },

  async createRequest(payload: CreateRequestPayload): Promise<HealthcareRequest> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 400));
      const newReq: HealthcareRequest = {
        id: `req-${Date.now().toString().slice(-4)}`,
        patient_id: payload.patient_id,
        request_type: payload.request_type as any,
        title: payload.title || `${payload.request_type} Request`,
        medicine_id: payload.medicine_id,
        facility_id: payload.facility_id,
        camp_id: payload.camp_id,
        preferred_date: payload.preferred_date,
        contact_phone: payload.contact_phone,
        extra_metadata: payload.extra_metadata,
        description: payload.description,
        urgency: payload.urgency as any,
        status: 'PENDING',
        created_at: new Date().toISOString(),
        recommendations: [
          {
            rank: 1,
            facility_id: 'f2-maholi-chc',
            facility_name: 'Community Health Centre (CHC) Maholi',
            facility_type: 'CHC',
            suitability_score: 0.91,
            medicine_confidence: 0.88,
            travel_distance_km: 11,
            travel_cost: 35,
            failure_probability: 0.12,
            expected_loss: 4,
            doctor_status: 'PRESENT',
            explanation: 'Automated NALAM AI recommendation: Balanced proximity with verified staff attendance and high medicine stock.',
          },
          {
            rank: 2,
            facility_id: 'f1-rampur-phc',
            facility_name: 'Primary Health Centre (PHC) Rampur',
            facility_type: 'PHC',
            suitability_score: 0.74,
            travel_distance_km: 2,
            travel_cost: 10,
            failure_probability: 0.35,
            expected_loss: 4,
            doctor_status: 'PRESENT',
            explanation: 'Closest primary centre for immediate preliminary consultation.',
          },
        ],
      };
      mockRequestsState = [newReq, ...mockRequestsState];
      saveRequestId(newReq.id);
      return newReq;
    }

    // 1. POST /api/requests
    const res = await apiRequest<{
      id: string;
      status: string;
      created_at: string;
      title?: string;
      request_type?: string;
      patient_id?: string;
      medicine_id?: string;
      facility_id?: string;
      camp_id?: string;
      preferred_date?: string;
      contact_phone?: string;
      extra_metadata?: string;
      description?: string;
      urgency?: string;
    }>('/api/requests', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    saveRequestId(res.id);

    // 2. Generate recommendations via POST /api/recommendations (non-blocking for user)
    let recs: RecommendationItem[] = [];
    try {
      recs = await recommendationService.generateRecommendations(res.id);
    } catch (recErr) {
      console.warn('Failed to generate initial recommendations:', recErr);
    }

    const created: HealthcareRequest = {
      id: res.id,
      patient_id: payload.patient_id,
      request_type: (res.request_type as any) || (payload.request_type as any),
      title: res.title || payload.title || `${payload.request_type} Request`,
      medicine_id: res.medicine_id || payload.medicine_id,
      facility_id: res.facility_id || payload.facility_id,
      camp_id: res.camp_id || payload.camp_id,
      preferred_date: res.preferred_date || payload.preferred_date,
      contact_phone: res.contact_phone || payload.contact_phone,
      extra_metadata: res.extra_metadata || payload.extra_metadata,
      description: res.description || payload.description,
      urgency: (res.urgency as any) || (payload.urgency as any),
      status: (res.status as any) || 'PENDING',
      created_at: res.created_at || new Date().toISOString(),
      recommendations: recs,
    };

    return created;
  },
};
