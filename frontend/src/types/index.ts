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
    is_expanded?: boolean;
    effective_radius_km?: number;
    initial_radius_km?: number;
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

export type CampCategory =
  | 'GENERAL_HEALTH_CAMP'
  | 'MOBILE_MEDICAL_UNIT'
  | 'NCD_SCREENING'
  | 'EYE_CAMP'
  | 'MATERNAL_CHILD_HEALTH'
  | 'VACCINATION_DRIVE'
  | 'SPECIALIST_OUTREACH'
  | string;

export interface HealthCamp {
  id: string;
  title: string;
  description: string;
  category: CampCategory;
  organizing_dept: string;
  start_date: string;
  end_date?: string;
  venue_name: string;
  full_address: string;
  village?: string;
  town?: string;
  taluk?: string;
  district: string;
  latitude?: number;
  longitude?: number;
  services_offered: string[];
  eligibility?: string;
  registration_instructions?: string;
  contact_info?: string;
  source_id?: string;
  source_org: string;
  source_url: string;
  publication_date?: string;
  discovered_at: string;
  last_checked_at: string;
  verification_status: 'VERIFIED' | 'UNVERIFIED' | 'FLAGGED' | 'REJECTED';
  event_status: 'UPCOMING' | 'ONGOING' | 'COMPLETED' | 'CANCELLED' | 'POSTPONED' | 'DATE_UNCONFIRMED';
  followup_instructions?: string;
  followup_facility_id?: string;
  provenance: Record<string, any>;
  distance_km?: number;
  created_at: string;
  updated_at: string;
}

export interface HealthCampListResponse {
  items: HealthCamp[];
  total: number;
  user_location?: { latitude: number; longitude: number };
  filters_applied: Record<string, any>;
}

export interface DistrictCoverageItem {
  district: string;
  district_ta: string;
  headquarters: string;
  portal_url: string;
  verified_events_count: number;
  last_checked_at?: string;
  check_status: 'SUCCESS' | 'PENDING' | 'ERROR';
  coverage_status: 'VERIFIED_EVENTS_AVAILABLE' | 'NO_PUBLISHED_EVENTS' | 'INSUFFICIENT_DATA';
}

export interface DistrictCoverageResponse {
  districts: DistrictCoverageItem[];
  total_districts: number;
  total_verified_camps: number;
  districts_with_events_count: number;
  monitored_sources_count: number;
  last_collection_timestamp?: string;
}

export interface HealthCampSource {
  id: string;
  name: string;
  organization: string;
  source_url: string;
  collector_type: string;
  district?: string;
  is_active: boolean;
  check_interval_hours: number;
  last_checked_at?: string;
  last_status: string;
  last_error?: string;
  events_discovered_count: number;
  created_at: string;
  updated_at: string;
}

export interface UserCampPreference {
  user_id: string;
  opt_in: boolean;
  preferred_districts: string[];
  max_distance_km: number;
  notify_categories: string[];
}

