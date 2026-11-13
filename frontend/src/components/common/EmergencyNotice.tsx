import React from 'react';
import { AlertCircle, Phone } from 'lucide-react';
import { cn } from '../../lib/utils';

export const EmergencyNotice: React.FC<{ className?: string }> = ({ className }) => {
  return (
    <div className={cn('bg-slate-100/90 border border-slate-200/90 rounded-xl p-3.5 text-xs text-slate-700 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2', className)}>
      <div className="flex items-start gap-2.5">
        <AlertCircle className="h-4 w-4 text-healthcare-700 flex-shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong className="text-slate-900">Medical Safety Notice:</strong> NALAM assists in facility discovery, verified stock check, and appointment booking. It is not a diagnostic engine and does not provide clinical diagnosis, prescription, or dosage advice.
        </p>
      </div>
      <div className="flex items-center gap-1.5 font-semibold text-rose-700 bg-rose-50 px-2.5 py-1 rounded-md border border-rose-200/80 flex-shrink-0">
        <Phone className="h-3.5 w-3.5" /> Emergency Ambulance: 108 / 102
      </div>
    </div>
  );
};
