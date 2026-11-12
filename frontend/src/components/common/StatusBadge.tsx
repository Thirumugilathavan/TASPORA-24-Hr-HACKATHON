import React from 'react';
import { cn } from '../../lib/utils';
import { getAvailabilityLabel, getUrgencyLabel } from '../../lib/constants';
import { useTranslation } from '../../context/LanguageContext';

interface StatusBadgeProps {
  status: string;
  type?: 'urgency' | 'availability' | 'appointment' | 'attendance' | 'generic';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = 'generic', className }) => {
  const { t } = useTranslation();

  if (type === 'urgency') {
    const config = getUrgencyLabel(status, t);
    return (
      <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border', config.color, className)}>
        {config.label}
      </span>
    );
  }

  if (type === 'availability') {
    const config = getAvailabilityLabel(status, t);
    return (
      <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border', config.badge, className)}>
        {config.label}
      </span>
    );
  }

  if (type === 'appointment') {
    let colorClass = 'bg-slate-100 text-slate-800 border-slate-200';
    let label = status;
    const norm = status ? status.toUpperCase() : '';

    if (norm === 'BOOKED') {
      colorClass = 'bg-teal-50 text-teal-800 border-teal-200';
      label = t('apptBooked', 'Booked');
    } else if (norm === 'CONFIRMED') {
      colorClass = 'bg-emerald-50 text-emerald-800 border-emerald-200';
      label = t('apptConfirmed', 'Confirmed');
    } else if (norm === 'CANCELLED') {
      colorClass = 'bg-rose-50 text-rose-800 border-rose-200';
      label = t('apptCancelled', 'Cancelled');
    } else if (norm === 'COMPLETED') {
      colorClass = 'bg-blue-50 text-blue-800 border-blue-200';
      label = t('apptCompleted', 'Completed');
    }

    return (
      <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border', colorClass, className)}>
        {label}
      </span>
    );
  }

  if (type === 'attendance') {
    let colorClass = 'bg-slate-100 text-slate-700';
    let label = `Doctor: ${status}`;
    const norm = status ? status.toUpperCase() : '';

    if (norm === 'PRESENT') {
      colorClass = 'bg-emerald-100 text-emerald-800';
      label = t('doctorPresent', 'Doctor: Present');
    } else if (norm === 'EXPECTED') {
      colorClass = 'bg-amber-100 text-amber-800';
      label = t('doctorExpected', 'Doctor: Expected');
    } else if (norm === 'ABSENT') {
      colorClass = 'bg-rose-100 text-rose-800';
      label = t('doctorAbsent', 'Doctor: Absent');
    }

    return (
      <span className={cn('inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', colorClass, className)}>
        {label}
      </span>
    );
  }

  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200', className)}>
      {status}
    </span>
  );
};
