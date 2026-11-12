import React, { useState, useEffect } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { AppointmentCard } from '../components/appointments/AppointmentCard';
import { BookAppointmentModal } from '../components/appointments/BookAppointmentModal';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { Appointment } from '../types';
import { appointmentService } from '../services/appointmentService';
import { useNotification } from '../context/NotificationContext';
import { useTranslation } from '../context/LanguageContext';
import { formatDate } from '../lib/utils';
import { PlusCircle } from 'lucide-react';

export const AppointmentsPage: React.FC = () => {
  const { notify } = useNotification();
  const { t } = useTranslation();

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'UPCOMING' | 'PAST'>('UPCOMING');
  const [isBookModalOpen, setIsBookModalOpen] = useState(false);
  const [cancelTarget, setCancelTarget] = useState<Appointment | null>(null);

  useEffect(() => {
    loadAppointments();
  }, []);

  const loadAppointments = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await appointmentService.getAppointments();
      setAppointments(data);
    } catch (err: any) {
      setError(err.message || t('errorTitle', 'Failed to load appointments.'));
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmCancel = async () => {
    if (!cancelTarget) return;
    try {
      await appointmentService.cancelAppointment(cancelTarget.id);
      notify(t('appointmentCancelledNotify', 'Appointment cancelled successfully.'), 'info');
      setCancelTarget(null);
      await loadAppointments();
    } catch (err: any) {
      notify(err.message || t('errorTitle', 'Failed to cancel appointment'), 'error');
    }
  };

  const upcomingAppointments = appointments.filter(
    (a) => a.status === 'BOOKED' || a.status === 'CONFIRMED'
  );

  const pastAppointments = appointments.filter(
    (a) => a.status === 'COMPLETED' || a.status === 'CANCELLED'
  );

  const displayList = activeTab === 'UPCOMING' ? upcomingAppointments : pastAppointments;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <PageHeader
          title={t('appointmentsTitle', 'Scheduled Appointments')}
          subtitle={t('appointmentsSubtitle', 'Manage direct consultations, queue tokens, and doctor visits across nearby health centers')}
        />
        <button
          onClick={() => setIsBookModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-xl shadow-sm transition-colors flex-shrink-0"
        >
          <PlusCircle className="w-4 h-4" />
          {t('bookAnAppointment', 'Book Appointment')}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('UPCOMING')}
          className={`pb-3 px-3 text-sm font-semibold transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === 'UPCOMING'
              ? 'border-emerald-600 text-emerald-700'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <span>{t('tabUpcoming', 'Upcoming Appointments')}</span>
          <span className="px-2 py-0.5 rounded-full text-xs bg-emerald-100 text-emerald-800">
            {upcomingAppointments.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('PAST')}
          className={`pb-3 px-3 text-sm font-semibold transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === 'PAST'
              ? 'border-emerald-600 text-emerald-700'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <span>{t('tabPast', 'Completed & Cancelled')}</span>
          <span className="px-2 py-0.5 rounded-full text-xs bg-slate-100 text-slate-600">
            {pastAppointments.length}
          </span>
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <LoadingState message={t('fetchingAppointments', 'Loading your appointments...')} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadAppointments} />
      ) : displayList.length === 0 ? (
        <EmptyState
          title={activeTab === 'UPCOMING' ? t('noAppointmentsScheduled', 'No upcoming appointments') : t('noPastAppointments', 'No past appointments')}
          message={
            activeTab === 'UPCOMING'
              ? t('needToSeeDoctor', 'You have no doctor visits or consultations booked. Schedule an appointment at a nearby center anytime.')
              : t('noPastAppointments', 'No past or cancelled appointments recorded.')
          }
          actionLabel={activeTab === 'UPCOMING' ? t('bookAnAppointment', 'Book an Appointment') : undefined}
          onAction={activeTab === 'UPCOMING' ? () => setIsBookModalOpen(true) : undefined}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {displayList.map((appt) => (
            <AppointmentCard
              key={appt.id}
              appointment={appt}
              onCancel={(target) => setCancelTarget(target)}
            />
          ))}
        </div>
      )}

      {/* Book Appointment Modal */}
      <BookAppointmentModal
        isOpen={isBookModalOpen}
        onClose={() => setIsBookModalOpen(false)}
        onSuccess={(newAppt) => {
          setAppointments([newAppt, ...appointments]);
        }}
      />

      {/* Cancel Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!cancelTarget}
        title={t('cancelApptTitle', 'Cancel Appointment')}
        message={t('cancelApptMessage', {
          facility: cancelTarget?.facility_name || '',
          date: cancelTarget ? formatDate(cancelTarget.appointment_date, t) : '',
        })}
        confirmLabel={t('yesCancel', 'Yes, Cancel')}
        cancelLabel={t('cancel', 'Cancel')}
        isDestructive
        onConfirm={handleConfirmCancel}
        onCancel={() => setCancelTarget(null)}
      />
    </div>
  );
};
