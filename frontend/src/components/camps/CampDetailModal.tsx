import React from 'react';
import {
  X,
  Calendar,
  Clock,
  MapPin,
  Building2,
  Phone,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  HeartHandshake,
  Navigation,
  FileText,
  Info,
} from 'lucide-react';
import { HealthCamp } from '../../types';

interface CampDetailModalProps {
  camp: HealthCamp | null;
  onClose: () => void;
}

export const CampDetailModal: React.FC<CampDetailModalProps> = ({ camp, onClose }) => {
  if (!camp) return null;

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'MOBILE_MEDICAL_UNIT':
        return 'Mobile Medical Unit (Hospital on Wheels)';
      case 'NCD_SCREENING':
        return 'NCD & Chronic Care Screening';
      case 'EYE_CAMP':
        return 'Specialist Eye & Cataract Camp';
      case 'MATERNAL_CHILD_HEALTH':
        return 'Maternal & Child Health';
      case 'VACCINATION_DRIVE':
        return 'Public Immunization Session';
      case 'SPECIALIST_OUTREACH':
        return 'Specialist Medical Outreach';
      default:
        return 'General Health Camp';
    }
  };

  const directionsUrl =
    camp.latitude && camp.longitude
      ? `https://www.google.com/maps/dir/?api=1&destination=${camp.latitude},${camp.longitude}`
      : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
          `${camp.venue_name}, ${camp.district}, Tamil Nadu`
        )}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs overflow-y-auto">
      <div
        className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200"
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <div className="bg-linear-to-r from-emerald-800 to-teal-900 p-6 text-white relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 text-emerald-100 hover:text-white hover:bg-white/10 rounded-full transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/30 text-emerald-100 border border-emerald-400/30">
              {getCategoryLabel(camp.category)}
            </span>
            {camp.verification_status === 'VERIFIED' ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-400 text-emerald-950">
                <ShieldCheck className="w-3.5 h-3.5" />
                Verified Government Notice
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-400 text-amber-950">
                <AlertTriangle className="w-3.5 h-3.5" />
                Unverified Announcement
              </span>
            )}
            {camp.distance_km !== undefined && camp.distance_km !== null && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white/20 text-white backdrop-blur-xs">
                {camp.distance_km.toFixed(1)} km away
              </span>
            )}
          </div>

          <h2 className="text-xl font-bold leading-snug">{camp.title}</h2>
          <p className="text-emerald-100 text-xs mt-1 flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 shrink-0" />
            {camp.organizing_dept}
          </p>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {/* Key Schedule & Venue Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm">
            <div className="space-y-1">
              <span className="text-xs font-medium text-slate-500 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-emerald-700" /> Date & Day
              </span>
              <p className="font-semibold text-slate-800">{formatDate(camp.start_date)}</p>
              <p className="text-xs text-slate-600 flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-400" />
                {formatTime(camp.start_date)}
                {camp.end_date ? ` – ${formatTime(camp.end_date)}` : ''}
              </p>
            </div>

            <div className="space-y-1">
              <span className="text-xs font-medium text-slate-500 flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-rose-600" /> Venue & Location
              </span>
              <p className="font-semibold text-slate-800">{camp.venue_name}</p>
              <p className="text-xs text-slate-600">{camp.full_address}</p>
            </div>
          </div>

          {/* Action Row */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <a
              href={directionsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-700 text-white hover:bg-emerald-800 transition-colors shadow-xs"
            >
              <Navigation className="w-3.5 h-3.5" />
              Get Directions via Google Maps
            </a>

            <a
              href={camp.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors border border-slate-300"
            >
              <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
              View Official Government Source Notice
            </a>
          </div>

          {/* Description */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
              Program Overview
            </h3>
            <p className="text-sm text-slate-700 leading-relaxed bg-white border border-slate-100 p-3.5 rounded-xl">
              {camp.description}
            </p>
          </div>

          {/* Services Offered */}
          {camp.services_offered && camp.services_offered.length > 0 && (
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Services Offered Free of Cost
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {camp.services_offered.map((svc, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2 p-2.5 rounded-lg bg-emerald-50/70 border border-emerald-100 text-xs text-emerald-950 font-medium"
                  >
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>{svc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Eligibility & Instructions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            {camp.eligibility && (
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <span className="font-bold text-slate-700 block mb-1">Target Beneficiaries & Eligibility</span>
                <p className="text-slate-600">{camp.eligibility}</p>
              </div>
            )}

            {camp.registration_instructions && (
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <span className="font-bold text-slate-700 block mb-1">Registration & Token Process</span>
                <p className="text-slate-600">{camp.registration_instructions}</p>
              </div>
            )}
          </div>

          {/* Follow-up Care Section */}
          <div className="p-4 rounded-xl bg-teal-50 border border-teal-200">
            <div className="flex items-center gap-2 mb-2 text-teal-900 font-bold text-sm">
              <HeartHandshake className="w-4 h-4 text-teal-700" />
              <span>Official Follow-up Care & Medication Refills</span>
            </div>
            <p className="text-xs text-teal-800 leading-relaxed">
              {camp.followup_instructions ||
                'Patients identified with conditions requiring continuing care should visit their nearest Primary Health Centre (PHC) with camp documentation. Contact 104 for coordination.'}
            </p>
          </div>

          {/* Provenance & Official Source Audit */}
          <div className="p-3.5 rounded-xl bg-slate-100 border border-slate-200 text-xs text-slate-600 space-y-1.5">
            <div className="flex items-center justify-between text-slate-700 font-semibold">
              <span className="flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-slate-500" /> Official Government Provenance
              </span>
              <span className="text-[11px] text-slate-500">
                Discovered: {new Date(camp.discovered_at).toLocaleDateString()}
              </span>
            </div>
            <p>
              <strong className="text-slate-700">Publishing Authority:</strong> {camp.source_org}
            </p>
            <p className="break-all">
              <strong className="text-slate-700">Official Source URL:</strong>{' '}
              <a
                href={camp.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-700 hover:underline"
              >
                {camp.source_url}
              </a>
            </p>
            {camp.contact_info && (
              <p>
                <strong className="text-slate-700">District Contact:</strong> {camp.contact_info}
              </p>
            )}
          </div>

          {/* Medical Notice */}
          <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs">
            <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <p>
              NALAM AI aggregates verified public notices published by the Government of Tamil Nadu and District Health Societies. All health camps and government doctor consultations are free of charge. Emergency ambulance: 108.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 text-xs font-semibold rounded-lg bg-slate-200 text-slate-700 hover:bg-slate-300 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
