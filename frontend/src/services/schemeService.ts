import { apiRequest } from './apiClient';
import {
  GovernmentScheme,
  SchemeRecommendationResponse,
  UserSchemeProfile,
  SavedScheme,
  CompareSchemesResponse,
  DocumentChecklistResponse,
} from '../types/index';

export interface SchemeQueryParams {
  category?: string;
  level?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export const schemeService = {
  async getQuestionnaireConfig(): Promise<any> {
    return apiRequest<any>('/api/schemes/questionnaire/config');
  },

  async getUserProfile(): Promise<UserSchemeProfile> {
    return apiRequest<UserSchemeProfile>('/api/schemes/profile');
  },

  async saveUserProfile(data: {
    consent_given: boolean;
    step_progress: number;
    profile_data: Record<string, any>;
  }): Promise<UserSchemeProfile> {
    return apiRequest<UserSchemeProfile>('/api/schemes/profile', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async deleteUserProfile(): Promise<{ status: string; message: string }> {
    return apiRequest<{ status: string; message: string }>('/api/schemes/profile', {
      method: 'DELETE',
    });
  },

  async getRecommendations(params: {
    category?: string;
    level?: string;
    language?: string;
  } = {}): Promise<SchemeRecommendationResponse> {
    const queryParams = new URLSearchParams();
    if (params.category && params.category !== 'ALL') queryParams.append('category', params.category);
    if (params.level && params.level !== 'ALL') queryParams.append('level', params.level);
    if (params.language) queryParams.append('language', params.language);

    const qs = queryParams.toString();
    const endpoint = `/api/schemes/recommendations${qs ? `?${qs}` : ''}`;
    return apiRequest<SchemeRecommendationResponse>(endpoint);
  },

  async getSchemes(params: SchemeQueryParams = {}): Promise<GovernmentScheme[]> {
    const queryParams = new URLSearchParams();
    if (params.category && params.category !== 'ALL') queryParams.append('category', params.category);
    if (params.level && params.level !== 'ALL') queryParams.append('level', params.level);
    if (params.search?.trim()) queryParams.append('search', params.search.trim());
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.offset) queryParams.append('offset', params.offset.toString());

    const qs = queryParams.toString();
    const endpoint = `/api/schemes${qs ? `?${qs}` : ''}`;
    return apiRequest<GovernmentScheme[]>(endpoint);
  },

  async getSchemeById(id: string): Promise<GovernmentScheme> {
    return apiRequest<GovernmentScheme>(`/api/schemes/${id}`);
  },

  async getSavedSchemes(): Promise<SavedScheme[]> {
    return apiRequest<SavedScheme[]>('/api/schemes/user/saved');
  },

  async saveScheme(schemeId: string, notes?: string): Promise<{ status: string; message: string }> {
    return apiRequest<{ status: string; message: string }>(`/api/schemes/${schemeId}/save`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  },

  async removeSavedScheme(schemeId: string): Promise<{ status: string; message: string }> {
    return apiRequest<{ status: string; message: string }>(`/api/schemes/${schemeId}/save`, {
      method: 'DELETE',
    });
  },

  async compareSchemes(schemeIds: string[]): Promise<CompareSchemesResponse> {
    return apiRequest<CompareSchemesResponse>('/api/schemes/compare', {
      method: 'POST',
      body: JSON.stringify({ scheme_ids: schemeIds }),
    });
  },

  async getDocumentChecklist(schemeIds?: string[]): Promise<DocumentChecklistResponse> {
    return apiRequest<DocumentChecklistResponse>('/api/schemes/documents/checklist', {
      method: 'POST',
      body: JSON.stringify({ scheme_ids: schemeIds }),
    });
  },
};
