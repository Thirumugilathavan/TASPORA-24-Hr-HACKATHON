import React from 'react';
import { Facility } from '../../types';
import { FACILITY_TYPE_LABELS } from '../../lib/constants';
import { formatDistance, formatDate } from '../../lib/utils';
import { X, MapPin, Phone, Clock, Stethoscope, CheckCircle, Calendar } from 'lucide-react';
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
  if (!facility) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/45 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-xl border border-slate-200 max-h-[90vh] flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-start justify-between p-6 border-b border-slate-100 bg-slate-50/50">
          <div>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-healthcare-100 text-healthcare-800 mb-2">
              {FACILITY_TYPE_LABELS[facility.facility_type] || facility.facility_type}
            </span>
            <h3 className="text-xl font-bold text-navy-900">{facility.name}</h3>
            <p className="mt-1 text-xs text-slate-500 flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5 text-slate-400" />
              {facility.address || `${facility.district} District`} • {formatDistance(facility.distance_km)}
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
                  <strong className="text-slate-900 block">Phone Helpline:</strong>
                  {facility.contact_number}
                </span>
              </div>
            )}
            {facility.operating_hours && (
              <div className="flex items-center gap-2.5 text-slate-700">
                <Clock className="h-4 w-4 text-healthcare-600 flex-shrink-0" />
                <span>
                  <strong className="text-slate-900 block">Operating Hours:</strong>
                  {facility.operating_hours}
                </span>
              </div>
            )}
          </div>

          {/* Doctors on Duty */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
              <Stethoscope className="h-4 w-4 text-healthcare-700" /> Doctors & Medical Staff
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
                          Verified {formatDate(doc.last_verified_at)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">No specific doctor schedules registered for this facility.</p>
            )}
          </div>

          {/* Services Provided */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-healthcare-700" /> Available Healthcare Services
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {facility.services.map((service, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 text-xs font-medium text-slate-700 bg-slate-50 py-2 px-3 rounded-lg border border-slate-100"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-healthcare-500" />
                  {service}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 px-6 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
          <p className="text-xs text-slate-500">
            Directions and travel advisory provided upon booking.
          </p>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
            >
              Close
            </button>
            <button
              type="button"
              onClick={() => {
                onClose();
                onBookAppointment(facility);
              }}
              className="px-4 py-2 text-xs font-semibold text-white bg-healthcare-600 rounded-lg hover:bg-healthcare-700 shadow-sm flex items-center gap-1.5"
            >
              <Calendar className="h-3.5 w-3.5" /> Book Appointment Here
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
