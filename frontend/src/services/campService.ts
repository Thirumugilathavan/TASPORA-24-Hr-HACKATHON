import { apiRequest } from './apiClient';
import {
  HealthCamp,
  HealthCampListResponse,
  DistrictCoverageResponse,
  DistrictCoverageItem,
  HealthCampSource,
  UserCampPreference,
} from '../types/index';

export interface CampQueryParams {
  query?: string;
  district?: string;
  category?: string;
  verification_status?: string;
  event_status?: string;
  date_range?: string;
  user_lat?: number;
  user_lng?: number;
  max_distance_km?: number;
  limit?: number;
  offset?: number;
}

export const campService = {
  async getHealthCamps(params: CampQueryParams = {}): Promise<HealthCampListResponse> {
    const queryParams = new URLSearchParams();
    if (params.query?.trim()) queryParams.append('query', params.query.trim());
    if (params.district && params.district !== 'ALL') queryParams.append('district', params.district);
    if (params.category && params.category !== 'ALL') queryParams.append('category', params.category);
    if (params.verification_status) queryParams.append('verification_status', params.verification_status);
    if (params.event_status) queryParams.append('event_status', params.event_status);
    if (params.date_range) queryParams.append('date_range', params.date_range);
    if (params.user_lat !== undefined && params.user_lat !== null) queryParams.append('user_lat', params.user_lat.toString());
    if (params.user_lng !== undefined && params.user_lng !== null) queryParams.append('user_lng', params.user_lng.toString());
    if (params.max_distance_km) queryParams.append('max_distance_km', params.max_distance_km.toString());
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.offset) queryParams.append('offset', params.offset.toString());

    const qs = queryParams.toString();
    const endpoint = `/api/camps${qs ? `?${qs}` : ''}`;
    return apiRequest<HealthCampListResponse>(endpoint);
  },

  async getCampById(id: string): Promise<HealthCamp> {
    return apiRequest<HealthCamp>(`/api/camps/${id}`);
  },

  async getDistrictCoverage(): Promise<DistrictCoverageResponse> {
    return apiRequest<DistrictCoverageResponse>('/api/camps/coverage');
  },

  async getDistricts(): Promise<Array<{ name: string; name_ta: string; headquarters: string; portal_url: string; latitude: number; longitude: number }>> {
    return apiRequest<Array<{ name: string; name_ta: string; headquarters: string; portal_url: string; latitude: number; longitude: number }>>('/api/camps/districts');
  },

  async getSources(): Promise<HealthCampSource[]> {
    return apiRequest<HealthCampSource[]>('/api/camps/sources');
  },

  async triggerSync(): Promise<{ sources_processed: number; sources_succeeded: number; total_new_events: number; details: any[] }> {
    return apiRequest('/api/camps/sync', { method: 'POST' });
  },

  async getUserPreferences(): Promise<UserCampPreference> {
    return apiRequest<UserCampPreference>('/api/camps/preferences');
  },

  async updateUserPreferences(pref: Partial<UserCampPreference>): Promise<UserCampPreference> {
    return apiRequest<UserCampPreference>('/api/camps/preferences', {
      method: 'PUT',
      body: JSON.stringify(pref),
    });
  },

  async updateVerification(id: string, updateData: { verification_status: string; event_status?: string; notes?: string }): Promise<HealthCamp> {
    return apiRequest<HealthCamp>(`/api/camps/${id}/verification`, {
      method: 'PATCH',
      body: JSON.stringify(updateData),
    });
  },
};
