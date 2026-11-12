import { apiRequest } from './apiClient';

export interface PincodeResolution {
  pincode: string;
  locality: string;
  district: string;
  state: string;
  latitude: number;
  longitude: number;
  is_approximate: boolean;
  confidence: 'EXACT' | 'POSTAL_CIRCLE';
  message: string;
}

export interface IVRFacilitySummary {
  id: string;
  name: string;
  facility_type: string;
  address: string;
  district: string;
  state: string;
  latitude: number;
  longitude: number;
  distance_km: number;
}

export interface IVRSimulationResponse {
  call_sid: string;
  status: string;
  current_menu: string;
  language: 'ta' | 'en';
  speak_text: string;
  speak_text_ta?: string;
  speak_text_en?: string;
  gather_dtmf?: boolean;
  max_digits?: number;
  location_name?: string;
  is_approximate?: boolean;
  latitude?: number;
  longitude?: number;
  total_found?: number;
  facilities?: IVRFacilitySummary[];
  current_index?: number;
  supports_pincode?: boolean;
  supports_geolocation?: boolean;
  supports_village?: boolean;
}

export const ivrSimulationService = {
  /**
   * Start a simulated IVR call session starting at Language Selection.
   */
  async startSimulation(language: 'ta' | 'en' = 'ta'): Promise<IVRSimulationResponse> {
    return await apiRequest<IVRSimulationResponse>('/api/ivr/simulation/start', {
      method: 'POST',
      body: JSON.stringify({ language }),
    });
  },

  /**
   * Submit DTMF keypad digits, PIN code, or GPS location to the simulation state machine.
   */
  async sendInput(payload: {
    call_sid: string;
    digits: string;
    current_menu: string;
    language: 'ta' | 'en';
    location_data?: any;
  }): Promise<IVRSimulationResponse> {
    return await apiRequest<IVRSimulationResponse>('/api/ivr/simulation/input', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Resolve a 6-digit Indian PIN code to postal centroid coordinates.
   */
  async resolvePincode(pincode: string): Promise<PincodeResolution> {
    const clean = pincode.trim();
    return await apiRequest<PincodeResolution>(`/api/pincodes/resolve?pincode=${encodeURIComponent(clean)}`, {
      method: 'GET',
    });
  },
};
