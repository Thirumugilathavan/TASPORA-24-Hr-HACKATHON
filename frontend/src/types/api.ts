import {
  Appointment,
  Facility,
  HealthcareRequest,
  Medicine,
  Patient,
  RecommendationItem,
  Role,
  StockAvailabilityItem,
  Village,
} from './index';

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

export interface PageResponse<T> {
  items: T[];
  total: number;
}

export interface RegisterRequest {
  name: string;
  phone: string;
  password: string;
  role: Role;
  village_id?: string;
  date_of_birth?: string;
  preferred_language?: string;
  emergency_contact_phone?: string;
  consent_given?: boolean;
}

export interface RegisterResponse {
  id: string;
  name: string;
  phone: string;
  role: Role;
  created_at?: string;
}

export interface LoginRequest {
  phone: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: Role;
  user_id: string;
}

export interface CreatePatientRequest {
  village_id: string;
  date_of_birth: string;
  preferred_language: string;
  consent_given?: boolean;
  emergency_contact_phone?: string;
}

export interface CreateRequestPayload {
  patient_id: string;
  request_type: string;
  medicine_id?: string;
  description: string;
  urgency: string;
}

export interface CreateAppointmentPayload {
  patient_id: string;
  facility_id: string;
  doctor_id?: string;
  request_id?: string;
  appointment_date: string;
  appointment_time: string;
}
