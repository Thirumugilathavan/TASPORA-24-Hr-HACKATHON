import React, { useState, useEffect } from 'react';
import { X, Calendar, Clock, Building2, User, AlertCircle, CheckCircle } from 'lucide-react';
import { Facility, Doctor, Appointment } from '../../types';
import { facilityService } from '../../services/facilityService';
import { appointmentService } from '../../services/appointmentService';
import { useAuth } from '../../context/AuthContext';
import { useNotification } from '../../context/NotificationContext';
import { useTranslation } from '../../context/LanguageContext';

interface BookAppointmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (appointment: Appointment) => void;
  initialFacilityId?: string;
  initialDoctorId?: string;
  requestId?: string;
}

const TIME_SLOTS = [
  { label: '09:00 AM', value: '09:00:00' },
  { label: '10:00 AM', value: '10:00:00' },
  { label: '11:00 AM', value: '11:00:00' },
  { label: '11:30 AM', value: '11:30:00' },
  { label: '02:00 PM', value: '14:00:00' },
  { label: '02:45 PM', value: '14:45:00' },
  { label: '03:30 PM', value: '15:30:00' },
  { label: '04:15 PM', value: '16:15:00' },
];

export const BookAppointmentModal: React.FC<BookAppointmentModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialFacilityId,
  initialDoctorId,
  requestId,
}) => {
  const { currentPatient, user } = useAuth();
  const { notify } = useNotification();
  const { t } = useTranslation();

  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacilityId, setSelectedFacilityId] = useState(initialFacilityId || '');
  const [selectedDoctorId, setSelectedDoctorId] = useState(initialDoctorId || '');
  const [date, setDate] = useState('');
  const [timeSlot, setTimeSlot] = useState(TIME_SLOTS[0].value);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Set default date to tomorrow
  useEffect(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    setDate(tomorrow.toISOString().split('T')[0]);
  }, []);

  useEffect(() => {
    if (initialFacilityId) setSelectedFacilityId(initialFacilityId);
    if (initialDoctorId) setSelectedDoctorId(initialDoctorId);
  }, [initialFacilityId, initialDoctorId]);

  useEffect(() => {
    if (isOpen) {
      loadFacilities();
    }
  }, [isOpen]);

  const loadFacilities = async () => {
    try {
      setLoading(true);
      const data = await facilityService.getFacilities();
      setFacilities(data);
      if (!selectedFacilityId && data.length > 0) {
        setSelectedFacilityId(data[0].id);
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const selectedFacility = facilities.find((f) => f.id === selectedFacilityId);
  const availableDoctors: Doctor[] = selectedFacility?.doctors || [];

  const minDate = new Date().toISOString().split('T')[0];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFacilityId) {
      setError(t('selectFacility', 'Please select a healthcare facility.'));
      return;
    }
    if (!date) {
      setError(t('appointmentDate', 'Please select an appointment date.'));
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const patientId = currentPatient?.id || user?.id || 'pat-sample-1';

      const appt = await appointmentService.bookAppointment({
        patient_id: patientId,
        facility_id: selectedFacilityId,
        doctor_id: selectedDoctorId || undefined,
        request_id: requestId,
        appointment_date: date,
        appointment_time: timeSlot,
      });

      notify(t('appointmentBookedNotify', 'Appointment booked successfully!'), 'success');
      if (onSuccess) onSuccess(appt);
      onClose();
    } catch (err: any) {
      setError(err.message || t('errorTitle', 'Failed to book appointment. Please try again.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-100 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-emerald-600" />
            <h2 className="text-lg font-semibold text-slate-800">{t('bookAppointmentTitle', 'Book Care Appointment')}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-sm text-rose-700 flex items-start gap-2">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Facility Select */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {t('selectFacility', 'Healthcare Facility')} <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <Building2 className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
              <select
                value={selectedFacilityId}
                onChange={(e) => {
                  setSelectedFacilityId(e.target.value);
                  setSelectedDoctorId(''); // reset doctor on facility change
                }}
                disabled={loading}
                className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
                required
              >
                {facilities.map((fac) => (
                  <option key={fac.id} value={fac.id}>
                    {fac.name} ({fac.facility_type}) — {fac.district}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Doctor Select */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {t('selectDoctor', 'Select Doctor (Optional)')}
            </label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
              <select
                value={selectedDoctorId}
                onChange={(e) => setSelectedDoctorId(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
              >
                <option value="">{t('anyDutyOfficer', 'Any Duty Medical Officer')}</option>
                {availableDoctors.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.name} ({doc.specialty})
                  </option>
                ))}
              </select>
            </div>
            {availableDoctors.length === 0 && (
              <p className="text-xs text-slate-500 mt-1">{t('generalOfficerNote', 'General Medical Officer will attend your consultation.')}</p>
            )}
          </div>

          {/* Date & Time Slot */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('appointmentDate', 'Date')} <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <Calendar className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="date"
                  min={minDate}
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('appointmentTime', 'Time Slot')} <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <Clock className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <select
                  value={timeSlot}
                  onChange={(e) => setTimeSlot(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
                  required
                >
                  {TIME_SLOTS.map((slot) => (
                    <option key={slot.value} value={slot.value}>
                      {slot.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="p-3 bg-emerald-50/60 rounded-lg border border-emerald-100 flex items-start gap-2.5 text-xs text-emerald-800">
            <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
            <span>
              {t('bookingGuaranteeNotice', 'Booking with CareBridge guarantees queued check-in and priority triage review at rural health centers.')}
            </span>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
            >
              {t('cancel', 'Cancel')}
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
            >
              {submitting ? t('confirmingAppointment', 'Confirming...') : t('confirmBooking', 'Confirm Appointment')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
