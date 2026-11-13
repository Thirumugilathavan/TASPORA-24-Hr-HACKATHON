import { apiRequest } from './apiClient';
import {
  GovernmentScheme,
  SchemeRecommendationResponse,
  UserSchemeProfile,
  SavedScheme,
  CompareSchemesResponse,
  DocumentChecklistResponse,
  SchemeMatchResponse,
} from '../types/index';
import { VERIFIED_SCHEMES_CATALOG } from '../data/verifiedSchemesCatalog';
import { evaluateLocalSchemeMatches, QuestionnaireFormAnswers } from './localSchemeMatcher';

export interface SchemeQueryParams {
  category?: string;
  level?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export const schemeService = {
  async getHealth(): Promise<any> {
    try {
      return await apiRequest<any>('/api/schemes/health');
    } catch {
      return {
        status: 'ok',
        service: 'NALAM Government Schemes (Offline Cache)',
        database: 'offline_fallback',
        total_schemes: VERIFIED_SCHEMES_CATALOG.length,
        sources: [
          'National Government Services Portal (services.india.gov.in)',
          'myScheme Welfare Portal (myscheme.gov.in)',
          'Tamil Nadu e-Governance Agency (tnega.tn.gov.in)',
          'Chief Minister Comprehensive Health Insurance Scheme (cmchistn.com)',
        ],
        last_catalog_verification: 'November 2026',
        timestamp: new Date().toISOString(),
      };
    }
  },

  async matchSchemes(
    answers: QuestionnaireFormAnswers,
    language: string = 'ta'
  ): Promise<{ data: SchemeMatchResponse; isOffline: boolean }> {
    try {
      const payload = { ...answers, language };
      const response = await apiRequest<SchemeMatchResponse>('/api/schemes/match', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      return { data: response, isOffline: false };
    } catch (err) {
      console.warn('Backend scheme match endpoint unreachable, falling back to verified local catalog:', err);
      const localResult = evaluateLocalSchemeMatches(answers, language);
      return { data: localResult, isOffline: true };
    }
  },

  async getQuestionnaireConfig(): Promise<any> {
    try {
      return await apiRequest<any>('/api/schemes/questionnaire/config');
    } catch {
      return {
        title_en: 'Find Government Schemes & Subsidies for Me',
        title_ta: 'எனக்கான அரசு நலத்திட்டங்களை கண்டறிக',
        privacy_notice_en:
          'Privacy Notice: Your information is collected solely to assess your eligibility for government subsidies and financial welfare schemes. All questions are optional, and sensitive personal data is never shared with third parties.',
        privacy_notice_ta:
          'தனியுரிமை அறிவிப்பு: உங்கள் தகவல்கள் அரசு மானியங்கள் மற்றும் நலத்திட்டங்களுக்கான தகுதியை மதிப்பிடுவதற்கு மட்டுமே சேகரிக்கப்படுகின்றன. உங்கள் தனிப்பட்ட தரவு மூன்றாம் தரப்பினருடன் பகிரப்படாது.',
        total_steps: 8,
      };
    }
  },

  async getUserProfile(): Promise<UserSchemeProfile | null> {
    try {
      return await apiRequest<UserSchemeProfile>('/api/schemes/profile');
    } catch {
      return null;
    }
  },

  async saveUserProfile(data: {
    consent_given: boolean;
    step_progress: number;
    profile_data: Record<string, any>;
  }): Promise<UserSchemeProfile | null> {
    try {
      return await apiRequest<UserSchemeProfile>('/api/schemes/profile', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    } catch {
      // Store in localStorage if offline
      if (typeof window !== 'undefined') {
        localStorage.setItem('nalam_scheme_profile', JSON.stringify(data));
      }
      return null;
    }
  },

  async deleteUserProfile(): Promise<{ status: string; message: string }> {
    try {
      return await apiRequest<{ status: string; message: string }>('/api/schemes/profile', {
        method: 'DELETE',
      });
    } catch {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('nalam_scheme_profile');
      }
      return { status: 'success', message: 'Local profile cleared.' };
    }
  },

  async getRecommendations(params: {
    category?: string;
    level?: string;
    language?: string;
  } = {}): Promise<{ data: SchemeRecommendationResponse; isOffline: boolean }> {
    const queryParams = new URLSearchParams();
    if (params.category && params.category !== 'ALL') queryParams.append('category', params.category);
    if (params.level && params.level !== 'ALL') queryParams.append('level', params.level);
    if (params.language) queryParams.append('language', params.language);

    const qs = queryParams.toString();
    const endpoint = `/api/schemes/recommendations${qs ? `?${qs}` : ''}`;
    try {
      const res = await apiRequest<SchemeRecommendationResponse>(endpoint);
      return { data: res, isOffline: false };
    } catch (err) {
      console.warn('Failed to fetch recommendations from API, evaluating from local catalog:', err);
      const localMatch = evaluateLocalSchemeMatches({}, params.language || 'ta');
      const recs: SchemeRecommendationResponse = {
        total_evaluated: localMatch.total_evaluated,
        likely_eligible_count: localMatch.likely_matches_count,
        possibly_eligible_count: localMatch.more_info_needed_count,
        more_info_count: localMatch.more_info_needed_count,
        recommendations: localMatch.all_results.map((r) => ({
          scheme: r.scheme,
          eligibility_status: r.match_status === 'LIKELY_MATCH' ? 'LIKELY_ELIGIBLE' : 'POSSIBLY_ELIGIBLE',
          match_score: r.match_score,
          matched_reasons: r.reasons,
          unverified_conditions: r.missing_information,
          missing_fields: r.missing_information,
          required_documents: r.required_documents,
          is_saved: false,
        })),
        disclaimer: localMatch.disclaimer_en,
        disclaimer_ta: localMatch.disclaimer_ta,
      };
      return { data: recs, isOffline: true };
    }
  },

  async getSchemes(params: SchemeQueryParams = {}): Promise<{ data: GovernmentScheme[]; isOffline: boolean }> {
    const queryParams = new URLSearchParams();
    if (params.category && params.category !== 'ALL') queryParams.append('category', params.category);
    if (params.level && params.level !== 'ALL') queryParams.append('level', params.level);
    if (params.search?.trim()) queryParams.append('search', params.search.trim());
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.offset) queryParams.append('offset', params.offset.toString());

    const qs = queryParams.toString();
    const endpoint = `/api/schemes${qs ? `?${qs}` : ''}`;
    try {
      const res = await apiRequest<GovernmentScheme[]>(endpoint);
      return { data: res, isOffline: false };
    } catch (err) {
      console.warn('API unavailable for schemes list, returning verified catalog fallback:', err);
      let list = [...VERIFIED_SCHEMES_CATALOG] as unknown as GovernmentScheme[];
      if (params.category && params.category !== 'ALL') {
        list = list.filter((s) => s.category === params.category);
      }
      if (params.level && params.level !== 'ALL') {
        list = list.filter((s) => s.level === params.level);
      }
      if (params.search?.trim()) {
        const q = params.search.trim().toLowerCase();
        list = list.filter(
          (s) =>
            s.name.toLowerCase().includes(q) ||
            s.name_ta.toLowerCase().includes(q) ||
            s.short_description.toLowerCase().includes(q) ||
            s.department.toLowerCase().includes(q)
        );
      }
      return { data: list, isOffline: true };
    }
  },

  async getSchemeById(id: string): Promise<GovernmentScheme> {
    try {
      return await apiRequest<GovernmentScheme>(`/api/schemes/${id}`);
    } catch {
      const found = VERIFIED_SCHEMES_CATALOG.find((s) => s.id === id || s.slug === id);
      if (found) return found as unknown as GovernmentScheme;
      throw new Error(`Scheme not found: ${id}`);
    }
  },

  async getSavedSchemes(): Promise<SavedScheme[]> {
    try {
      return await apiRequest<SavedScheme[]>('/api/schemes/user/saved');
    } catch {
      if (typeof window !== 'undefined') {
        const raw = localStorage.getItem('nalam_saved_scheme_ids');
        if (raw) {
          const ids: string[] = JSON.parse(raw);
          return ids.map((id) => {
            const scheme = VERIFIED_SCHEMES_CATALOG.find((s) => s.id === id || s.slug === id) || ({} as any);
            return {
              id,
              scheme_id: id,
              saved_at: new Date().toISOString(),
              scheme: scheme as GovernmentScheme,
            };
          });
        }
      }
      return [];
    }
  },

  async saveScheme(schemeId: string, notes?: string): Promise<{ status: string; message: string }> {
    try {
      return await apiRequest<{ status: string; message: string }>(`/api/schemes/${schemeId}/save`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      });
    } catch {
      if (typeof window !== 'undefined') {
        const raw = localStorage.getItem('nalam_saved_scheme_ids');
        const ids: string[] = raw ? JSON.parse(raw) : [];
        if (!ids.includes(schemeId)) ids.push(schemeId);
        localStorage.setItem('nalam_saved_scheme_ids', JSON.stringify(ids));
      }
      return { status: 'success', message: 'Saved locally.' };
    }
  },

  async removeSavedScheme(schemeId: string): Promise<{ status: string; message: string }> {
    try {
      return await apiRequest<{ status: string; message: string }>(`/api/schemes/${schemeId}/save`, {
        method: 'DELETE',
      });
    } catch {
      if (typeof window !== 'undefined') {
        const raw = localStorage.getItem('nalam_saved_scheme_ids');
        if (raw) {
          const ids: string[] = JSON.parse(raw);
          const filtered = ids.filter((id) => id !== schemeId);
          localStorage.setItem('nalam_saved_scheme_ids', JSON.stringify(filtered));
        }
      }
      return { status: 'success', message: 'Removed locally.' };
    }
  },

  async compareSchemes(schemeIds: string[]): Promise<CompareSchemesResponse> {
    try {
      return await apiRequest<CompareSchemesResponse>('/api/schemes/compare', {
        method: 'POST',
        body: JSON.stringify({ scheme_ids: schemeIds }),
      });
    } catch {
      const schemes = VERIFIED_SCHEMES_CATALOG.filter((s) => schemeIds.includes(s.id) || schemeIds.includes(s.slug)) as unknown as GovernmentScheme[];
      return {
        schemes,
        comparison_fields: [
          { key: 'category', label_en: 'Category', label_ta: 'பிரிவு' },
          { key: 'level', label_en: 'Level', label_ta: 'அரசு நிலை' },
          { key: 'department', label_en: 'Department', label_ta: 'அரசுத்துறை' },
          { key: 'benefit_amount_desc', label_en: 'Benefit Amount', label_ta: 'உதவித் தொகை' },
          { key: 'benefit_frequency', label_en: 'Frequency', label_ta: 'வழங்கும் கால இடைவெளி' },
          { key: 'application_mode', label_en: 'Application Mode', label_ta: 'விண்ணப்பிக்கும் முறை' },
        ],
      };
    }
  },

  async getDocumentChecklist(schemeIds?: string[]): Promise<DocumentChecklistResponse> {
    try {
      return await apiRequest<DocumentChecklistResponse>('/api/schemes/documents/checklist', {
        method: 'POST',
        body: JSON.stringify({ scheme_ids: schemeIds }),
      });
    } catch {
      const selected = VERIFIED_SCHEMES_CATALOG.filter(
        (s) => !schemeIds || schemeIds.length === 0 || schemeIds.includes(s.id) || schemeIds.includes(s.slug)
      );
      const docMap = new Map<string, any>();
      selected.forEach((s) => {
        (s.required_documents || []).forEach((d) => {
          const key = d.name_en.toLowerCase().trim();
          if (!docMap.has(key)) {
            docMap.set(key, {
              name_en: d.name_en,
              name_ta: d.name_ta,
              is_mandatory: d.is_mandatory,
              description_en: d.description_en,
              description_ta: d.description_ta,
              required_for_schemes: [s.name],
              required_for_schemes_ta: [s.name_ta],
            });
          } else {
            const existing = docMap.get(key);
            if (!existing.required_for_schemes.includes(s.name)) {
              existing.required_for_schemes.push(s.name);
              existing.required_for_schemes_ta.push(s.name_ta);
            }
          }
        });
      });

      const allDocs = Array.from(docMap.values());
      return {
        total_documents: allDocs.length,
        mandatory_documents: allDocs.filter((d) => d.is_mandatory),
        optional_documents: allDocs.filter((d) => !d.is_mandatory),
        schemes_covered: selected.map((s) => ({ id: s.id, name: s.name, name_ta: s.name_ta })),
      };
    }
  },
};

