import React from 'react';
import { Facility } from '../../types';
import { getFacilityTypeLabel } from '../../lib/constants';
import { formatDistance, formatDate } from '../../lib/utils';
import { useTranslation } from '../../context/LanguageContext';
import { X, MapPin, Phone, Stethoscope, CheckCircle, Calendar } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';

interface FacilityDetailModalProps {
  facility: Facility | null;
  onClose: () => void;
  onBookAppointment: (facility: Facility) => void;
}

export const FacilityDetailModal: React.FC<FacilityDetailModalProps> = ({
  facility,
  onClose,
  onBookAppointment,
}) => {
  const { t } = useTranslation();
  if (!facility) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/45 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-xl border border-slate-200 max-h-[90vh] flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-start justify-between p-6 border-b border-slate-100 bg-slate-50/50">
          <div>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-healthcare-100 text-healthcare-800 mb-2">
              {getFacilityTypeLabel(facility.facility_type, t)}
            </span>
            <h3 className="text-xl font-bold text-navy-900">{facility.name}</h3>
            <p className="mt-1 text-xs text-slate-500 flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5 text-slate-400" />
              {facility.address || `${facility.district} ${t('district', 'District')}`} • {formatDistance(facility.distance_km, t)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/60 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Contact & Hours */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50/80 p-4 rounded-xl border border-slate-200/60 text-xs">
            {facility.contact_number && (
              <div className="flex items-center gap-2.5 text-slate-700">
                <Phone className="h-4 w-4 text-healthcare-600 flex-shrink-0" />
                <span>
                  <strong className="text-slate-900 block">{t('phoneHelpline', 'Phone Helpline:')}</strong>
                  {facility.contact_number}
                </span>
              </div>
            )}
            {facility.directions_url && (
              <div className="flex items-center gap-2.5 text-slate-700">
                <MapPin className="h-4 w-4 text-emerald-600 flex-shrink-0" />
                <span>
                  <strong className="text-slate-900 block">{t('navigation', 'Navigation:')}</strong>
                  <a
                    href={facility.directions_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-emerald-700 hover:underline font-semibold"
                  >
                    {t('openInGoogleMaps', 'Open in Google Maps ↗')}
                  </a>
                </span>
              </div>
            )}
            {facility.ownership && (
              <div className="flex items-center gap-2.5 text-slate-700">
                <span className="h-4 w-4 rounded-full bg-slate-200 text-[10px] font-bold flex items-center justify-center text-slate-600">G</span>
                <span>
                  <strong className="text-slate-900 block">{t('facilityOwnership', 'Facility Ownership:')}</strong>
                  {facility.ownership}
                </span>
              </div>
            )}
          </div>

          {/* Operational Availability Note */}
          <div className="p-3 bg-amber-50/70 rounded-xl border border-amber-200/80 text-xs text-amber-900">
            <p className="font-semibold flex items-center gap-1.5">
              <span>⚠️ </span> {t('availNotVerified', 'Availability Not Verified')}
            </p>
            <p className="text-[11px] text-amber-800 mt-0.5">
              {t('availNotVerifiedDesc', 'Distances are calculated geographically from your location. Live attendance and medicine stock are subject to real-time verification before travel.')}
            </p>
          </div>

          {/* Doctors on Duty */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
              <Stethoscope className="h-4 w-4 text-healthcare-700" /> {t('doctorsMedicalStaff', 'Doctors & Medical Staff')}
            </h4>
            {facility.doctors && facility.doctors.length > 0 ? (
              <div className="space-y-2.5">
                {facility.doctors.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-3 rounded-lg border border-slate-200 bg-white flex items-center justify-between"
                  >
                    <div>
                      <p className="text-sm font-bold text-navy-900">{doc.name}</p>
                      <p className="text-xs text-slate-500">{doc.specialty}</p>
                    </div>
                    <div className="text-right">
                      {doc.attendance_status && (
                        <StatusBadge status={doc.attendance_status} type="attendance" />
                      )}
                      {doc.last_verified_at && (
                        <p className="text-[10px] text-slate-400 mt-1">
                          {t('verified', 'Verified')} {formatDate(doc.last_verified_at, t)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">{t('noDoctorSchedules', 'No specific doctor schedules registered for this facility.')}</p>
            )}
          </div>

          {/* Services Provided */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-healthcare-700" /> {t('availServices', 'Available Healthcare Services')}
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {(facility.services || []).length > 0 ? (
                (facility.services || []).map((service, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 text-xs font-medium text-slate-700 bg-slate-50 py-2 px-3 rounded-lg border border-slate-100"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-healthcare-500" />
                    {service}
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500 italic col-span-2">{t('standardServicesDesc', 'Standard primary outpatient and emergency care services available.')}</p>
              )}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 px-6 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
          <p className="text-xs text-slate-500">
            {t('travelAdvisoryNotice', 'Directions and travel advisory provided upon booking.')}
          </p>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              {t('close', 'Close')}
            </button>
            <button
              type="button"
              onClick={() => {
                onClose();
                onBookAppointment(facility);
              }}
              className="px-4 py-2 text-xs font-semibold text-white bg-healthcare-600 rounded-lg hover:bg-healthcare-700 shadow-sm flex items-center gap-1.5"
            >
              <Calendar className="h-3.5 w-3.5" /> {t('bookAppointmentHere', 'Book Appointment Here')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
