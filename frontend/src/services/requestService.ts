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
  async getRequests(patientId?: string): Promise<HealthcareRequest[]> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 200));
      return [...mockRequestsState];
    }

    const ids = getStoredRequestIds();
    if (ids.length === 0) {
      return [];
    }

    const requests: HealthcareRequest[] = [];
    for (const id of ids) {
      try {
        const req = await this.getRequestById(id);
        if (req && (!patientId || req.patient_id === patientId)) {
          // Attempt to load recommendations if not already present
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
        medicine_id: payload.medicine_id,
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
            explanation: 'Automated CareBridge recommendation: Balanced proximity with verified staff attendance and high medicine stock.',
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
      return newReq;
    }

    // 1. POST /api/requests
    const res = await apiRequest<{ id: string; status: string; created_at: string }>('/api/requests', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    saveRequestId(res.id);

    // 2. Generate recommendations via POST /api/recommendations
    let recs: RecommendationItem[] = [];
    try {
      recs = await recommendationService.generateRecommendations(res.id);
    } catch (recErr) {
      console.warn('Failed to generate initial recommendations:', recErr);
    }

    const created: HealthcareRequest = {
      id: res.id,
      patient_id: payload.patient_id,
      request_type: payload.request_type as any,
      medicine_id: payload.medicine_id,
      description: payload.description,
      urgency: payload.urgency as any,
      status: (res.status as any) || 'PENDING',
      created_at: res.created_at || new Date().toISOString(),
      recommendations: recs,
    };

    return created;
  },
};
