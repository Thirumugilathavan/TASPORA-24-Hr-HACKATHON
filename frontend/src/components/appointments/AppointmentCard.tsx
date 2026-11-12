import React from 'react';
import { Calendar, Clock, Stethoscope, XCircle } from 'lucide-react';
import { Appointment } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { formatDate } from '../../lib/utils';
import { useTranslation } from '../../context/LanguageContext';

interface AppointmentCardProps {
  appointment: Appointment;
  onCancel?: (appointment: Appointment) => void;
}

export const AppointmentCard: React.FC<AppointmentCardProps> = ({ appointment, onCancel }) => {
  const { t } = useTranslation();
  const canCancel = appointment.status === 'BOOKED' || appointment.status === 'CONFIRMED';

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-slate-900 text-lg">{appointment.facility_name}</h3>
          </div>
          <p className="text-sm text-slate-500 flex items-center gap-1.5">
            <Stethoscope className="w-4 h-4 text-emerald-600" />
            <span>{t('doctorAttendance', 'Doctor:')} </span>
            <strong className="text-slate-700 font-medium">
              {appointment.doctor_name || t('dutyMedicalOfficer', 'Duty Medical Officer')}
            </strong>
          </p>
        </div>
        <StatusBadge status={appointment.status} type="appointment" />
      </div>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 py-3 border-y border-slate-100 text-sm">
        <div className="flex items-center gap-2 text-slate-600">
          <Calendar className="w-4 h-4 text-slate-400" />
          <span>{t('appointmentDate', 'Date:')} </span>
          <span className="font-medium text-slate-800">{formatDate(appointment.appointment_date, t)}</span>
        </div>
        <div className="flex items-center gap-2 text-slate-600">
          <Clock className="w-4 h-4 text-slate-400" />
          <span>{t('appointmentTime', 'Slot:')} </span>
          <span className="font-medium text-slate-800">{appointment.appointment_time}</span>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
        <span>{t('bookingId', 'Booking ID:')} #{appointment.id.slice(-6).toUpperCase()}</span>
        {canCancel && onCancel && (
          <button
            onClick={() => onCancel(appointment)}
            className="inline-flex items-center gap-1 text-rose-600 hover:text-rose-700 hover:bg-rose-50 px-2.5 py-1.5 rounded-lg font-medium transition-colors"
          >
            <XCircle className="w-4 h-4" />
            {t('cancelAppointment', 'Cancel Appointment')}
          </button>
        )}
      </div>
    </div>
  );
};
