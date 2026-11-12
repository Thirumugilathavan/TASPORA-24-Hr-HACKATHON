import React from 'react';
import { Facility } from '../../types';
import { formatDistance } from '../../lib/utils';
import { getFacilityTypeLabel } from '../../lib/constants';
import { useTranslation } from '../../context/LanguageContext';
import { MapPin, Stethoscope, ChevronRight, Clock } from 'lucide-react';

interface FacilityCardProps {
  facility: Facility;
  onViewDetails: (facility: Facility) => void;
  onBookAppointment?: (facility: Facility) => void;
}

export const FacilityCard: React.FC<FacilityCardProps> = ({
  facility,
  onViewDetails,
  onBookAppointment,
}) => {
  const { t } = useTranslation();
  const typeLabel = getFacilityTypeLabel(facility.facility_type, t);

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm p-5 hover:border-healthcare-400 hover:shadow-md transition-all duration-200 flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-3 mb-2.5">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-healthcare-50 text-healthcare-800 border border-healthcare-200">
            {typeLabel}
          </span>
          <span className="text-xs font-medium text-slate-500 flex items-center gap-1">
            <MapPin className="h-3.5 w-3.5 text-slate-400" />
            {formatDistance(facility.distance_km, t)}
          </span>
        </div>

        <h3 className="text-base font-bold text-navy-900 leading-snug">{facility.name}</h3>

        <p className="mt-1.5 text-xs text-slate-500 line-clamp-1">
          {facility.address || `${facility.village_name || t('ruralBlock', 'Rural block')}, ${t('district', 'District')} ${facility.district}`}
        </p>

        {facility.operating_hours && (
          <p className="mt-1 text-xs text-slate-500 flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-slate-400" /> {facility.operating_hours}
          </p>
        )}

        {/* Doctor Summary */}
        {facility.doctors && facility.doctors.length > 0 && (
          <div className="mt-3 py-2 px-2.5 bg-slate-50 rounded-lg text-xs text-slate-700 flex items-center gap-2">
            <Stethoscope className="h-3.5 w-3.5 text-healthcare-600 flex-shrink-0" />
            <span className="truncate">
              <strong>{facility.doctors[0].name}</strong> ({facility.doctors[0].specialty})
            </span>
          </div>
        )}

        {/* Services Chips */}
        {facility.services && facility.services.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {facility.services.slice(0, 3).map((service, idx) => (
              <span
                key={idx}
                className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium"
              >
                {service}
              </span>
            ))}
            {facility.services.length > 3 && (
              <span className="text-[11px] px-1.5 py-0.5 text-slate-400 font-medium">
                +{facility.services.length - 3} {t('more', 'more')}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={() => onViewDetails(facility)}
          className="text-xs font-semibold text-healthcare-700 hover:text-healthcare-800 flex items-center gap-1 transition-colors py-1"
        >
          {t('viewFacilityDetails', 'View Facility Details')} <ChevronRight className="h-3.5 w-3.5" />
        </button>

        {onBookAppointment && (
          <button
            type="button"
            onClick={() => onBookAppointment(facility)}
            className="px-3 py-1.5 bg-healthcare-600 hover:bg-healthcare-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
          >
            {t('bookVisit', 'Book Visit')}
          </button>
        )}
      </div>
    </div>
  );
};
