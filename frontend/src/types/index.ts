export type Role = 'PATIENT' | 'ASHA' | 'DOCTOR' | 'STAFF' | 'ADMIN';

export type FacilityType = 'PHC' | 'CHC' | 'HOSPITAL' | 'PHARMACY' | 'SCE' | 'THO' | 'DHO' | 'SUB_CENTRE' | string;

export type AvailabilityStatus = 'IN_STOCK' | 'LOW' | 'OUT' | 'UNKNOWN';

export type AvailabilityLabel = 'LIKELY' | 'UNCERTAIN' | 'UNLIKELY';

export type RequestType = 'CONSULTATION' | 'REFILL' | 'CHECKUP' | 'DIAGNOSTIC';

export type Urgency = 'NORMAL' | 'PRIORITY' | 'URGENT';

export type AppointmentStatus = 'BOOKED' | 'CONFIRMED' | 'CANCELLED' | 'COMPLETED';

export type AttendanceStatus = 'EXPECTED' | 'PRESENT' | 'ABSENT' | 'UNKNOWN';

export interface User {
  id: string;
  name: string;
  phone: string;
  role: Role;
  created_at?: string;
}

export interface Village {
  id: string;
  name: string;
  district: string;
  state?: string;
  subdistrict?: string;
  latitude: number;
  longitude: number;
  is_synthetic?: boolean;
}

export interface Patient {
  id: string;
  user_id: string;
  name?: string;
  phone?: string;
  village_id: string;
  village?: Village;
  date_of_birth: string;
  preferred_language: string;
  consent_given?: boolean;
  emergency_contact_phone?: string;
  created_at?: string;
}

export interface Doctor {
  id: string;
  facility_id: string;
  name: string;
  specialty: string;
  attendance_status?: AttendanceStatus;
  last_verified_at?: string;
}

export interface Facility {
  id: string;
  name: string;
  facility_type: FacilityType;
  district: string;
  state?: string;
  subdistrict?: string;
  village_id?: string;
  village_name?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  distance_km?: number;
  ownership?: string;
  source?: string;
  source_id?: string;
  unverified_availability?: boolean;
  directions_url?: string;
  services?: string[];
  doctors?: Doctor[];
  contact_number?: string;
  contact_details?: Record<string, any>;
  operating_hours?: string;
  created_at?: string;
  updated_at?: string;
}

export interface NearbyFacilityListResponse {
  items: Facility[];
  total: number;
  skip?: number;
  limit?: number;
  has_more?: boolean;
  resolved_location: {
    latitude: number;
    longitude: number;
    source: string;
    label?: string;
    name?: string;
    district?: string;
    state?: string;
    subdistrict?: string;
    village_id?: string;
    patient_id?: string;
  };
  radius_km: number;
}

export interface Medicine {
  id: string;
  name: string;
  code: string;
  category: string;
  formulation?: string;
  description?: string;
}

export interface StockAvailabilityItem {
  facility_id: string;
  facility_name?: string;
  facility_type?: FacilityType;
  distance_km?: number;
  p_available?: number;
  confidence?: number;
  label: AvailabilityLabel;
  evidence_count?: number;
  last_report_at?: string;
}

export interface HealthcareRequest {
  id: string;
  patient_id: string;
  request_type: RequestType;
  medicine_id?: string;
  medicine_name?: string;
  description: string;
  urgency: Urgency;
  status: 'PENDING' | 'RECOMMENDED' | 'BOOKED' | 'COMPLETED' | 'CANCELLED';
  created_at: string;
  recommendations?: RecommendationItem[];
}

export interface RecommendationItem {
  rank: number;
  facility_id: string;
  facility_name: string;
  facility_type?: FacilityType;
  suitability_score?: number;
  medicine_confidence?: number;
  travel_distance_km?: number;
  travel_cost?: number;
  failure_probability?: number;
  expected_loss?: number;
  doctor_status?: AttendanceStatus;
  explanation: string;
}

export interface Appointment {
  id: string;
  patient_id: string;
  facility_id: string;
  facility_name: string;
  doctor_id?: string;
  doctor_name?: string;
  request_id?: string;
  appointment_date: string;
  appointment_time: string;
  status: AppointmentStatus;
  created_at?: string;
}
