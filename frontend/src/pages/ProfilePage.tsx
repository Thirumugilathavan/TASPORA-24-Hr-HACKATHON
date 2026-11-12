import React, { useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { useNotification } from '../context/NotificationContext';
import { LANGUAGES } from '../lib/constants';
import { LanguageCode } from '../lib/i18n';
import { config, toggleMockMode } from '../lib/config';
import {
  User,
  Phone,
  MapPin,
  Calendar,
  Languages,
  ShieldCheck,
  ToggleLeft,
  ToggleRight,
  LogOut,
  Info,
  Server,
  HeartHandshake,
} from 'lucide-react';

export const ProfilePage: React.FC = () => {
  const { user, currentPatient, setPreferredLanguage, logout } = useAuth();
  const { language, setLanguage, t } = useTranslation();
  const { notify } = useNotification();

  const [selectedLang, setSelectedLang] = useState(
    currentPatient?.preferred_language || language || 'ta'
  );

  const handleLanguageChange = (langCode: string) => {
    setSelectedLang(langCode);
    setPreferredLanguage(langCode);
    setLanguage(langCode as LanguageCode);
    notify('Preferred language updated successfully!', 'success');
  };

  const handleToggleMock = () => {
    const nextState = !config.isMockMode;
    toggleMockMode(nextState);
    notify(
      nextState
        ? 'Switched to Mock Data Mode.'
        : 'Switched to Live Backend API Mode (Connecting to http://localhost:8000).',
      'info'
    );
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <PageHeader
        title="Patient Profile & Settings"
        subtitle="Review your registered health identity, village association, and coordination preferences"
      />

      {/* Main Profile Information */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-2xl shadow-inner">
              {user?.name ? user.name.slice(0, 2).toUpperCase() : 'PT'}
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">{user?.name || 'Registered Patient'}</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {user?.role || 'PATIENT'}
                </span>
                <span className="text-xs text-slate-400">UID: {user?.id}</span>
              </div>
            </div>
          </div>

          <button
            onClick={logout}
            className="inline-flex items-center gap-1.5 px-4 py-2 border border-rose-200 text-rose-600 hover:bg-rose-50 text-sm font-medium rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 pt-6 text-sm">
          <div className="flex items-start gap-3">
            <Phone className="w-5 h-5 text-slate-400 mt-0.5" />
            <div>
              <p className="text-xs text-slate-500 font-medium">Registered Phone</p>
              <p className="text-slate-800 font-medium mt-0.5">{user?.phone || 'Not provided'}</p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <MapPin className="w-5 h-5 text-slate-400 mt-0.5" />
            <div>
              <p className="text-xs text-slate-500 font-medium">Home Village & District</p>
              <p className="text-slate-800 font-medium mt-0.5">
                {currentPatient?.village?.name || 'Thiruvallur'}, {currentPatient?.village?.district || 'Tamil Nadu'}
              </p>
              {currentPatient?.village?.latitude && (
                <p className="text-xs text-slate-400">
                  Lat: {currentPatient.village.latitude.toFixed(4)}, Long: {currentPatient.village.longitude.toFixed(4)}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Calendar className="w-5 h-5 text-slate-400 mt-0.5" />
            <div>
              <p className="text-xs text-slate-500 font-medium">Date of Birth</p>
              <p className="text-slate-800 font-medium mt-0.5">
                {currentPatient?.date_of_birth || '1990-01-01'}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Phone className="w-5 h-5 text-slate-400 mt-0.5" />
            <div>
              <p className="text-xs text-slate-500 font-medium">Emergency Contact</p>
              <p className="text-slate-800 font-medium mt-0.5">
                {currentPatient?.emergency_contact_phone || '9876543299 (ASHA)'}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 text-emerald-500 mt-0.5" />
            <div>
              <p className="text-xs text-slate-500 font-medium">Data Sharing Consent</p>
              <p className={currentPatient?.consent_given ? 'text-emerald-700 font-medium mt-0.5' : 'text-slate-500 font-medium mt-0.5'}>
                {currentPatient?.consent_given ? 'Granted (Clinical Coordination)' : 'Not Granted'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Language Preference */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Languages className="w-5 h-5 text-emerald-600" />
          <h3 className="font-semibold text-slate-900">Communication & Interface Language</h3>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Select your primary language for SMS notifications, triage instructions, and dashboard labels.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => handleLanguageChange(lang.code)}
              className={`p-3 rounded-lg border text-left transition-all ${
                selectedLang === lang.code
                  ? 'border-emerald-600 bg-emerald-50/70 ring-1 ring-emerald-500'
                  : 'border-slate-200 hover:border-slate-300 bg-white'
              }`}
            >
              <p className="font-semibold text-sm text-slate-800">{lang.nativeName}</p>
              <p className="text-xs text-slate-500">{lang.label}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Developer & Hackathon Demonstration Settings */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Server className="w-5 h-5 text-slate-600" />
          <h3 className="font-semibold text-slate-900">Demonstration & API Configuration</h3>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Switch between autonomous Mock Mode (self-contained for presentation) and Live Backend API.
        </p>

        <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 border border-slate-200">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm text-slate-800">Mock Data Mode</span>
              <span
                className={`px-2 py-0.5 rounded text-xs font-semibold ${
                  config.isMockMode
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-emerald-100 text-emerald-800'
                }`}
              >
                {config.isMockMode ? 'Enabled (Demo Mode)' : 'Disabled (Live API)'}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Backend endpoint target:{' '}
              <code className="text-xs bg-slate-200 px-1 py-0.5 rounded">{config.apiBaseUrl}</code>
            </p>
          </div>

          <button
            onClick={handleToggleMock}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium bg-white hover:bg-slate-100 border border-slate-300 rounded-lg shadow-sm transition-colors text-slate-700"
          >
            {config.isMockMode ? (
              <>
                <ToggleRight className="w-5 h-5 text-amber-500" />
                Switch to Live
              </>
            ) : (
              <>
                <ToggleLeft className="w-5 h-5 text-slate-400" />
                Switch to Mock
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
