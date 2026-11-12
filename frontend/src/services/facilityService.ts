import { config } from '../lib/config';
import { MOCK_FACILITIES } from '../mocks/data';
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
  skip?: number;
  limit?: number;
}

export const facilityService = {
  async getNearbyFacilities(params: NearbyFacilityParams = {}): Promise<NearbyFacilityListResponse> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 250));
      const sorted = [...MOCK_FACILITIES].map((f, idx) => ({
        ...f,
        distance_km: (idx + 1) * 2.3,
        unverified_availability: true,
        directions_url: `https://www.google.com/maps/dir/?api=1&destination=12.9716,79.1378`,
      }));
      return {
        items: sorted,
        total: sorted.length,
        resolved_location: {
          latitude: 12.9716,
          longitude: 79.1378,
          source: 'mock',
          label: 'Simulated Patient Location',
        },
        radius_km: params.radius_km || 10,
      };
    }

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
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 300));
      let results = [...MOCK_FACILITIES];

      if (filters.query) {
        const q = filters.query.toLowerCase();
        results = results.filter(
          (f) =>
            f.name.toLowerCase().includes(q) ||
            f.district.toLowerCase().includes(q) ||
            (f.village_name && f.village_name.toLowerCase().includes(q))
        );
      }

      if (filters.facility_type && filters.facility_type !== 'ALL') {
        results = results.filter((f) => f.facility_type === filters.facility_type);
      }

      if (filters.service && filters.service !== 'ALL') {
        results = results.filter((f) => (f.services || []).some((s) => s.toLowerCase().includes(filters.service!.toLowerCase())));
      }

      return results;
    }

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
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 200));
      const found = MOCK_FACILITIES.find((f) => f.id === id);
      if (!found) {
        throw new Error('Facility information unavailable.');
      }
      return found;
    }

    return await apiRequest<Facility>(`/api/facilities/${id}`);
  },
};
