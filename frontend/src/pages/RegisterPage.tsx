import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  HeartHandshake,
  User,
  Phone,
  Lock,
  Calendar,
  Languages,
  Eye,
  EyeOff,
  AlertCircle,
} from 'lucide-react';
import { Village } from '../types';
import { LANGUAGES } from '../lib/constants';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { useNotification } from '../context/NotificationContext';
import { EmergencyNotice } from '../components/common/EmergencyNotice';
import { LocationSearchInput } from '../components/common/LocationSearchInput';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();
  const { t } = useTranslation();
  const { notify } = useNotification();

  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [villageId, setVillageId] = useState('');
  const [selectedVillage, setSelectedVillage] = useState<Village | null>(null);
  const [dob, setDob] = useState('1990-01-01');
  const [language, setLanguage] = useState('ta');
  const [emergencyPhone, setEmergencyPhone] = useState('');
  const [consentGiven, setConsentGiven] = useState(false);

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLocationSelect = (village: Village | null) => {
    if (village) {
      setVillageId(village.id);
      setSelectedVillage(village);
      setError(null);
    } else {
      setVillageId('');
      setSelectedVillage(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !phone.trim() || !password || !dob) {
      setError(t('fillAllFieldsError', 'Please fill in all mandatory fields.'));
      return;
    }

    if (!villageId) {
      setError(t('selectValidLocationError', 'Please search and select a verified village, town, or city from the suggestions.'));
      return;
    }

    if (!consentGiven) {
      setError(t('consentRequiredError', 'You must grant consent to store your profile for healthcare coordination.'));
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await register(
        name.trim(),
        phone.trim(),
        password,
        villageId,
        dob,
        language,
        emergencyPhone.trim() || undefined,
        consentGiven
      );

      notify(t('welcomeNotify', 'Registration successful! Welcome to NALAM AI.'), 'success');
      navigate('/');
    } catch (err: any) {
      setError(err.message || t('errorTitle', 'Registration failed. Please check your information.'));
    } finally {
      setLoading(false);
    }
  };

  const maxDob = new Date().toISOString().split('T')[0];

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50/40 to-slate-100 flex flex-col justify-center py-10 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-lg px-4">
        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-600 text-white shadow-lg shadow-emerald-500/20 mb-3">
            <HeartHandshake className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('appName', 'NALAM AI')}</h1>
          <p className="text-sm text-slate-600 mt-1">{t('taglineSub', 'Rural Healthcare Accessibility & Coordination')}</p>
        </div>

        {/* Card */}
        <div className="mt-8 bg-white py-8 px-6 shadow-xl shadow-slate-200/50 sm:rounded-2xl sm:px-10 border border-slate-100">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-slate-800">{t('registerTitle', 'New Patient Registration')}</h2>
            <p className="text-xs text-slate-500 mt-1">
              {t('registerSubtitle', 'Create an account linked with your village healthcare network across India')}
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-sm text-rose-700 flex items-start gap-2">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('fullName', 'Full Name')} <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={t('enterFullNamePlaceholder', 'e.g. Ramesh Kumar')}
                  required
                  className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            {/* Phone & Password */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  {t('registeredPhone', 'Phone Number')} <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder={t('enterPhonePlaceholder', '10-digit mobile')}
                    required
                    className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  {t('password', 'Password')} <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={t('enterPasswordPlaceholder', 'Min 8 characters')}
                    required
                    className="w-full pl-9 pr-10 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>

            {/* Nationwide Village / Town / City Search */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('villageLocation', 'Home Village, Town, or City')} <span className="text-rose-500">*</span>
              </label>
              <LocationSearchInput
                selectedVillageId={villageId}
                onSelect={handleLocationSelect}
                required
                placeholder={t('searchVillagePlaceholder', 'Search across all Indian states...')}
              />
            </div>

            {/* Language Selection */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('preferredLanguage', 'Preferred Language')} <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <Languages className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
                  required
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.label} ({lang.nativeName})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* DOB & Emergency Contact */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  {t('dateOfBirth', 'Date of Birth')} <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <Calendar className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="date"
                    max={maxDob}
                    value={dob}
                    onChange={(e) => setDob(e.target.value)}
                    required
                    className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  {t('emergencyContactOptional', 'Emergency Contact Phone')}
                </label>
                <div className="relative">
                  <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="tel"
                    value={emergencyPhone}
                    onChange={(e) => setEmergencyPhone(e.target.value)}
                    placeholder="Relative / ASHA"
                    className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
                  />
                </div>
              </div>
            </div>

            {/* Consent Checkbox */}
            <div className="pt-2">
              <label className="flex items-start gap-2.5 text-xs text-slate-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={consentGiven}
                  onChange={(e) => setConsentGiven(e.target.checked)}
                  className="mt-0.5 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                />
                <span>
                  {t('consentGranted', 'I consent to sharing my healthcare requirements, medication history, and status updates with authorized NALAM AI health workers, doctors, and primary health centres.')}
                </span>
              </label>
            </div>

            <EmergencyNotice />

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full mt-4 flex items-center justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 transition-colors"
            >
              {loading ? t('registering', 'Creating Account & Profile...') : t('registerBtn', 'Complete Registration')}
            </button>
          </form>

          {/* Footer Link */}
          <div className="mt-6 text-center text-xs text-slate-600 space-y-2">
            <div>
              {t('alreadyHaveAccount', 'Already have a NALAM AI account?')}{' '}
              <Link to="/login" className="font-medium text-emerald-600 hover:text-emerald-500">
                {t('signInHere', 'Sign in here')}
              </Link>
            </div>
            <div className="pt-2 border-t border-slate-100">
              <span className="text-slate-500">No account or mobile internet?</span>{' '}
              <Link to="/ivr" className="font-semibold text-emerald-600 hover:text-emerald-700 underline">
                Dial Toll-Free Voice Helpline (Simulated IVR)
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
