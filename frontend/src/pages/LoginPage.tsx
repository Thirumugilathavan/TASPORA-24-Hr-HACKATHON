import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { HeartHandshake, Phone, Lock, Eye, EyeOff, LogIn, Sparkles, Zap } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { useNotification } from '../context/NotificationContext';
import { EmergencyNotice } from '../components/common/EmergencyNotice';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, loginDemoUser } = useAuth();
  const { t } = useTranslation();
  const { notify } = useNotification();

  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim() || !password) {
      setError('Please provide both phone number and password.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await login(phone.trim(), password);
      notify('Welcome back to NALAM!', 'success');
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoFill = () => {
    setPhone('9876543210');
    setPassword('DemoPass123!');
    setError(null);
  };

  const handleDemoLogin = () => {
    loginDemoUser();
    notify('Logged in as Demo Patient!', 'success');
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50/40 to-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md px-4">
        {/* Logo and title */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-600 text-white shadow-lg shadow-emerald-500/20 mb-3">
            <HeartHandshake className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">NALAM</h1>
          <p className="text-sm text-slate-600 mt-1">Rural Healthcare Accessibility & Coordination</p>
        </div>

        {/* Card */}
        <div className="mt-8 bg-white py-8 px-6 shadow-xl shadow-slate-200/50 sm:rounded-2xl sm:px-10 border border-slate-100">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-slate-800">Sign In to Your Account</h2>
            <p className="text-xs text-slate-500 mt-1">Access medical facilities, stock checks, and appointments</p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-sm text-rose-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Registered Phone Number
              </label>
              <div className="relative">
                <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="e.g. 9876543210"
                  required
                  className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
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

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <LogIn className="w-4 h-4" />
              {loading ? 'Signing in...' : t('signIn', 'Sign In')}
            </button>
          </form>

          {/* Quick Demo buttons */}
          <div className="mt-5 pt-4 border-t border-slate-100 space-y-2">
            <button
              type="button"
              onClick={handleDemoLogin}
              className="w-full py-2 px-3 border border-emerald-300 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-sm"
            >
              <Zap className="w-3.5 h-3.5 text-amber-300" />
              One-Click Demo Patient Login
            </button>
            <button
              type="button"
              onClick={handleDemoFill}
              className="w-full py-2 px-3 border border-emerald-200 bg-emerald-50/50 hover:bg-emerald-50 text-emerald-800 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              Fill Demo Credentials (9876543210)
            </button>
          </div>

          <div className="mt-6 text-center text-xs text-slate-500">
            Don't have an account yet?{' '}
            <Link to="/register" className="font-semibold text-emerald-600 hover:text-emerald-700">
              {t('register', 'Register as New Patient')}
            </Link>
          </div>
        </div>

        <div className="mt-6">
          <EmergencyNotice />
        </div>
      </div>
    </div>
  );
};
