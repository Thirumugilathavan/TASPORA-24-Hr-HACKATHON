import React from 'react';
import { Medicine, StockAvailabilityItem } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { formatDate, formatDistance } from '../../lib/utils';
import { useTranslation } from '../../context/LanguageContext';
import { Pill, Building2, Clock, AlertTriangle } from 'lucide-react';

interface MedicineCardProps {
  medicine: Medicine;
  stockItems?: StockAvailabilityItem[];
  availability?: StockAvailabilityItem[];
  onRequestRefill?: (medicine: Medicine) => void;
}

export const MedicineCard: React.FC<MedicineCardProps> = ({
  medicine,
  stockItems,
  availability,
  onRequestRefill,
}) => {
  const { t } = useTranslation();
  const items = stockItems || availability || [];

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm p-5 hover:border-healthcare-300 transition-all duration-200">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="h-10 w-10 rounded-xl bg-healthcare-50 text-healthcare-700 flex items-center justify-center flex-shrink-0">
            <Pill className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-navy-900">{medicine.name}</h3>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">
                {medicine.code}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {medicine.formulation && <span className="font-medium text-slate-700">{medicine.formulation} • </span>}
              {medicine.category}
            </p>
            {medicine.description && (
              <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">{medicine.description}</p>
            )}
          </div>
        </div>

        {onRequestRefill && (
          <button
            type="button"
            onClick={() => onRequestRefill(medicine)}
            className="flex-shrink-0 text-xs font-semibold px-3 py-1.5 bg-healthcare-50 text-healthcare-800 border border-healthcare-200 rounded-lg hover:bg-healthcare-100 transition-colors shadow-2xs"
          >
            {t('requestRefill', 'Request Refill')}
          </button>
        )}
      </div>

      {/* Reported Stock Locations */}
      <div className="mt-4 pt-3.5 border-t border-slate-100">
        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2.5">
          {t('stockLikelihoodTitle', 'Reported Facility Availability')}
        </p>

        {items && items.length > 0 ? (
          <div className="space-y-2">
            {items.map((item, idx) => (
              <div
                key={idx}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-2.5 bg-slate-50/80 rounded-lg border border-slate-200/60 text-xs gap-2"
              >
                <div className="flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-slate-400 flex-shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-900 block sm:inline">
                      {item.facility_name || t('designatedFacility', 'Designated Facility')}
                    </span>
                    {item.distance_km !== undefined && (
                      <span className="text-slate-500 text-[11px] sm:ml-2">
                        ({formatDistance(item.distance_km, t)})
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2.5 self-start sm:self-auto">
                  <StatusBadge status={item.label} type="availability" />

                  {item.last_report_at && (
                    <span className="text-[11px] text-slate-400 flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {t('reportedOn', 'Reported')} {formatDate(item.last_report_at, t)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-3 bg-slate-50 rounded-lg text-xs text-slate-500 text-center italic">
            {t('noStockReports', 'No active availability reports logged for this medicine in neighboring centers.')}
          </div>
        )}

        <p className="mt-2 text-[11px] text-slate-500 italic flex items-center gap-1">
          <AlertTriangle className="h-3 w-3 text-amber-500 inline" />
          {t('stockDisclaimer', 'Availability status represents recent field reports and may vary with real-time dispensary demand.')}
        </p>
      </div>
    </div>
  );
};
