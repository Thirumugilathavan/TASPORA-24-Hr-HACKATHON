export const LANGUAGES = [
  { code: 'en', label: 'English', nativeName: 'English' },
  { code: 'ta', label: 'Tamil', nativeName: 'தமிழ்' },
  { code: 'hi', label: 'Hindi', nativeName: 'हिंदी' },
  { code: 'te', label: 'Telugu', nativeName: 'తెలుగు' },
  { code: 'bn', label: 'Bengali', nativeName: 'বাংলা' },
];

export const FACILITY_TYPE_LABELS: Record<string, string> = {
  PHC: 'Primary Health Centre (PHC)',
  CHC: 'Community Health Centre (CHC)',
  HOSPITAL: 'District Hospital',
  PHARMACY: 'Community Jan Aushadhi Pharmacy',
  SCE: 'Health Sub-Centre (SCE)',
  SUB_CENTRE: 'Health Sub-Centre (SCE)',
  THO: 'Taluk Hospital (THO)',
  DHO: 'District Hospital (DHO)',
};

export const REQUEST_TYPE_LABELS: Record<string, string> = {
  CONSULTATION: 'Doctor Consultation',
  REFILL: 'Medicine Refill',
  CHECKUP: 'Routine Health Checkup',
  DIAGNOSTIC: 'Diagnostic / Lab Test',
};

export const URGENCY_LABELS: Record<string, { label: string; color: string }> = {
  NORMAL: { label: 'Normal Routine', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  PRIORITY: { label: 'Priority Attention', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  URGENT: { label: 'Urgent Care Required', color: 'bg-rose-50 text-rose-700 border-rose-200' },
};

export const AVAILABILITY_LABELS: Record<string, { label: string; color: string; badge: string }> = {
  LIKELY: {
    label: 'Likely Available',
    color: 'text-emerald-700',
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  },
  UNCERTAIN: {
    label: 'Uncertain / Limited',
    color: 'text-amber-700',
    badge: 'bg-amber-100 text-amber-800 border-amber-300',
  },
  UNLIKELY: {
    label: 'Likely Unavailable',
    color: 'text-rose-700',
    badge: 'bg-rose-100 text-rose-800 border-rose-300',
  },
};
