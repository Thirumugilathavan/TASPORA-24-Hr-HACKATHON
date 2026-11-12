import { config } from '../lib/config';
import { MOCK_FACILITIES } from '../mocks/data';
import { PageResponse } from '../types/api';
import { Facility } from '../types/index';
import { apiRequest } from './apiClient';

export interface FacilityFilters {
  query?: string;
  facility_type?: string;
  service?: string;
  village_id?: string;
}

export const facilityService = {
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
        results = results.filter((f) => f.services.some((s) => s.toLowerCase().includes(filters.service!.toLowerCase())));
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
