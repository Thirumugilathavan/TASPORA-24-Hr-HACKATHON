import React from 'react';
import { cn } from '../../lib/utils';
import { AVAILABILITY_LABELS, URGENCY_LABELS } from '../../lib/constants';

interface StatusBadgeProps {
  status: string;
  type?: 'urgency' | 'availability' | 'appointment' | 'attendance' | 'generic';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = 'generic', className }) => {
  if (type === 'urgency' && URGENCY_LABELS[status]) {
    const config = URGENCY_LABELS[status];
    return (
      <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border', config.color, className)}>
        {config.label}
      </span>
    );
  }

  if (type === 'availability' && AVAILABILITY_LABELS[status]) {
    const config = AVAILABILITY_LABELS[status];
    return (
      <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border', config.badge, className)}>
        {config.label}
      </span>
    );
  }

  if (type === 'appointment') {
    let colorClass = 'bg-slate-100 text-slate-800 border-slate-200';
    if (status === 'BOOKED') colorClass = 'bg-teal-50 text-teal-800 border-teal-200';
    if (status === 'CONFIRMED') colorClass = 'bg-emerald-50 text-emerald-800 border-emerald-200';
    if (status === 'CANCELLED') colorClass = 'bg-rose-50 text-rose-800 border-rose-200';
    if (status === 'COMPLETED') colorClass = 'bg-blue-50 text-blue-800 border-blue-200';

    return (
      <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border', colorClass, className)}>
        {status}
      </span>
    );
  }

  if (type === 'attendance') {
    let colorClass = 'bg-slate-100 text-slate-700';
    if (status === 'PRESENT') colorClass = 'bg-emerald-100 text-emerald-800';
    if (status === 'EXPECTED') colorClass = 'bg-amber-100 text-amber-800';
    if (status === 'ABSENT') colorClass = 'bg-rose-100 text-rose-800';

    return (
      <span className={cn('inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', colorClass, className)}>
        Doctor: {status}
      </span>
    );
  }

  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200', className)}>
      {status}
    </span>
  );
};
