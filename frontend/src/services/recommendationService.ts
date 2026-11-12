import { config } from '../lib/config';
import { MOCK_REQUESTS } from '../mocks/data';
import { RecommendationItem } from '../types/index';
import { apiRequest } from './apiClient';

export const recommendationService = {
  async getRecommendations(requestId: string): Promise<RecommendationItem[]> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 300));
      const request = MOCK_REQUESTS.find((req) => req.id === requestId);
      return request?.recommendations || [];
    }

    const res = await apiRequest<{ items: RecommendationItem[] }>(`/api/recommendations/${requestId}`);
    return res.items || [];
  },

  async generateRecommendations(requestId: string): Promise<RecommendationItem[]> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 600));
      return this.getRecommendations(requestId);
    }

    const res = await apiRequest<{ items: RecommendationItem[] }>('/api/recommendations', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId }),
    });
    return res.items || [];
  },
};
