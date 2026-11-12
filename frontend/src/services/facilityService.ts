import { PageResponse } from '../types/api';
import { Facility, NearbyFacilityListResponse } from '../types/index';
import { apiRequest } from './apiClient';

export interface FacilityFilters {
  query?: string;
  facility_type?: string;
  service?: string;
  village_id?: string;
}

export interface NearbyFacilityParams {
  latitude?: number;
  longitude?: number;
  village_id?: string;
  patient_id?: string;
  radius_km?: number;
  facility_type?: string;
  ownership?: string;
  query?: string;
  auto_expand?: boolean;
  skip?: number;
  limit?: number;
}

export const facilityService = {
  async getNearbyFacilities(params: NearbyFacilityParams = {}): Promise<NearbyFacilityListResponse> {
    const queryParams = new URLSearchParams();
    if (params.latitude !== undefined && params.latitude !== null) {
      queryParams.append('latitude', params.latitude.toString());
    }
    if (params.longitude !== undefined && params.longitude !== null) {
      queryParams.append('longitude', params.longitude.toString());
    }
    if (params.village_id) {
      queryParams.append('village_id', params.village_id);
    }
    if (params.patient_id) {
      queryParams.append('patient_id', params.patient_id);
    }
    if (params.radius_km !== undefined) {
      queryParams.append('radius_km', params.radius_km.toString());
    }
    if (params.facility_type && params.facility_type !== 'ALL') {
      queryParams.append('facility_type', params.facility_type);
    }
    if (params.ownership && params.ownership !== 'ALL') {
      queryParams.append('ownership', params.ownership);
    }
    if (params.query && params.query.trim()) {
      queryParams.append('query', params.query.trim());
    }
    if (params.auto_expand !== undefined) {
      queryParams.append('auto_expand', params.auto_expand ? 'true' : 'false');
    }
    if (params.skip !== undefined) {
      queryParams.append('skip', params.skip.toString());
    }
    if (params.limit !== undefined) {
      queryParams.append('limit', params.limit.toString());
    }

    const endpoint = `/api/facilities/nearby${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return await apiRequest<NearbyFacilityListResponse>(endpoint);
  },

  async getFacilities(filters: FacilityFilters = {}): Promise<Facility[]> {
    const queryParams = new URLSearchParams();
    if (filters.facility_type && filters.facility_type !== 'ALL') {
      queryParams.append('facility_type', filters.facility_type);
    }
    if (filters.service && filters.service !== 'ALL') {
      queryParams.append('service', filters.service);
    }
    if (filters.village_id) {
      queryParams.append('village_id', filters.village_id);
    }

    const endpoint = `/api/facilities${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    const res = await apiRequest<PageResponse<Facility> | Facility[]>(endpoint);
    return Array.isArray(res) ? res : res.items || [];
  },

  async getFacilityById(id: string): Promise<Facility> {
    return await apiRequest<Facility>(`/api/facilities/${id}`);
  },
};
