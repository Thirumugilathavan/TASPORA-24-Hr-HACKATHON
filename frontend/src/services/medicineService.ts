import { config } from '../lib/config';
import { MOCK_MEDICINES, MOCK_STOCK_AVAILABILITY } from '../mocks/data';
import { PageResponse } from '../types/api';
import { Medicine, StockAvailabilityItem } from '../types/index';
import { apiRequest } from './apiClient';

export const medicineService = {
  async getMedicines(query?: string): Promise<Medicine[]> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 250));
      if (!query || !query.trim()) {
        return MOCK_MEDICINES;
      }
      const q = query.toLowerCase();
      return MOCK_MEDICINES.filter(
        (m) =>
          m.name.toLowerCase().includes(q) ||
          m.code.toLowerCase().includes(q) ||
          m.category.toLowerCase().includes(q)
      );
    }

    const endpoint = `/api/medicines${query ? `?q=${encodeURIComponent(query)}` : ''}`;
    const res = await apiRequest<PageResponse<Medicine> | Medicine[]>(endpoint);
    return Array.isArray(res) ? res : res.items || [];
  },

  async getStockAvailability(medicineId: string, facilityIds?: string[]): Promise<StockAvailabilityItem[]> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 300));
      const items = MOCK_STOCK_AVAILABILITY[medicineId] || [];
      if (facilityIds && facilityIds.length > 0) {
        return items.filter((item) => facilityIds.includes(item.facility_id));
      }
      return items;
    }

    const queryParams = new URLSearchParams({ medicine_id: medicineId });
    if (facilityIds && facilityIds.length > 0) {
      queryParams.append('facility_ids', facilityIds.join(','));
    }

    const res = await apiRequest<{ items: StockAvailabilityItem[] }>(
      `/api/stock/availability?${queryParams.toString()}`
    );
    return res.items || [];
  },
};
