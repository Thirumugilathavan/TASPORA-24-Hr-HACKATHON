import { config } from '../lib/config';
import { MOCK_APPOINTMENTS, MOCK_FACILITIES } from '../mocks/data';
import { CreateAppointmentPayload } from '../types/api';
import { Appointment } from '../types/index';
import { apiRequest } from './apiClient';
import { facilityService } from './facilityService';

let mockAppointmentsState = [...MOCK_APPOINTMENTS];

function getStoredAppointmentIds(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem('nalam_my_appointment_ids') || localStorage.getItem('carebridge_my_appointment_ids');
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveAppointmentId(id: string) {
  if (typeof window === 'undefined') return;
  try {
    const ids = getStoredAppointmentIds();
    if (!ids.includes(id)) {
      ids.unshift(id);
      localStorage.setItem('nalam_my_appointment_ids', JSON.stringify(ids.slice(0, 50)));
      localStorage.setItem('carebridge_my_appointment_ids', JSON.stringify(ids.slice(0, 50)));
    }
  } catch {
    // Ignore storage errors
  }
}

export const appointmentService = {
  async getAppointments(patientId?: string): Promise<Appointment[]> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 200));
      return [...mockAppointmentsState];
    }

    const ids = getStoredAppointmentIds();
    if (ids.length === 0) {
      return [];
    }

    const appts: Appointment[] = [];
    for (const id of ids) {
      try {
        const appt = await apiRequest<Appointment>(`/api/appointments/${id}`);
        if (appt && (!patientId || appt.patient_id === patientId)) {
          // Enrich facility name if not populated
          if (!appt.facility_name && appt.facility_id) {
            try {
              const fac = await facilityService.getFacilityById(appt.facility_id);
              if (fac) appt.facility_name = fac.name;
            } catch {
              appt.facility_name = 'Healthcare Facility';
            }
          }
          appts.push(appt);
        }
      } catch (err) {
        console.warn(`Appointment ${id} could not be retrieved:`, err);
      }
    }
    return appts;
  },

  async bookAppointment(payload: CreateAppointmentPayload): Promise<Appointment> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 450));
      const facility = MOCK_FACILITIES.find((f) => f.id === payload.facility_id);

      const newAppt: Appointment = {
        id: `appt-${Date.now().toString().slice(-4)}`,
        patient_id: payload.patient_id,
        facility_id: payload.facility_id,
        facility_name: facility?.name || 'Care Facility',
        doctor_id: payload.doctor_id,
        doctor_name: facility?.doctors?.find((d) => d.id === payload.doctor_id)?.name || 'Duty Medical Officer',
        request_id: payload.request_id,
        appointment_date: payload.appointment_date,
        appointment_time: payload.appointment_time,
        status: 'BOOKED',
        created_at: new Date().toISOString(),
      };

      mockAppointmentsState = [newAppt, ...mockAppointmentsState];
      return newAppt;
    }

    // Call POST /api/appointments
    const res = await apiRequest<{ id: string; status: string }>('/api/appointments', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    saveAppointmentId(res.id);

    // Retrieve detailed appointment
    try {
      const detail = await apiRequest<Appointment>(`/api/appointments/${res.id}`);
      if (!detail.facility_name && detail.facility_id) {
        try {
          const fac = await facilityService.getFacilityById(detail.facility_id);
          if (fac) detail.facility_name = fac.name;
        } catch {
          detail.facility_name = 'Healthcare Facility';
        }
      }
      return detail;
    } catch {
      return {
        id: res.id,
        patient_id: payload.patient_id,
        facility_id: payload.facility_id,
        facility_name: 'Healthcare Facility',
        doctor_id: payload.doctor_id,
        request_id: payload.request_id,
        appointment_date: payload.appointment_date,
        appointment_time: payload.appointment_time,
        status: (res.status as any) || 'BOOKED',
        created_at: new Date().toISOString(),
      };
    }
  },

  async cancelAppointment(appointmentId: string): Promise<void> {
    if (config.isMockMode) {
      await new Promise((r) => setTimeout(r, 300));
      mockAppointmentsState = mockAppointmentsState.map((appt) =>
        appt.id === appointmentId ? { ...appt, status: 'CANCELLED' as const } : appt
      );
      return;
    }

    await apiRequest(`/api/appointments/${appointmentId}/cancel`, {
      method: 'PATCH',
    });
  },
};
