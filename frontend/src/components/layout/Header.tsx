import React, { useState } from 'react';
import { Menu, Bell, Globe, LogOut, ChevronDown, UserCircle2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTranslation } from '../../context/LanguageContext';
import { LANGUAGES } from '../../lib/constants';
import { Link, useNavigate } from 'react-router-dom';
import { LanguageCode } from '../../lib/i18n';

interface HeaderProps {
  onToggleSidebar: () => void;
  title?: string;
  breadcrumb?: string;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar, title, breadcrumb }) => {
  const { user, patient, logout, updateLanguage } = useAuth();
  const { language, setLanguage, t } = useTranslation();
  const [isLangOpen, setIsLangOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const navigate = useNavigate();

  const currentLang = LANGUAGES.find((l) => l.code === language) || LANGUAGES[1]; // Default Tamil

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200/90 px-4 md:px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="md:hidden p-2 text-slate-500 hover:text-slate-800 rounded-lg hover:bg-slate-100"
          aria-label={t('openSidebar', 'Open sidebar')}
        >
          <Menu className="h-5 w-5" />
        </button>

        <div>
          {breadcrumb && <span className="text-xs text-slate-500 font-medium">{breadcrumb}</span>}
          {title && <h1 className="text-base font-bold text-navy-900 leading-tight">{title}</h1>}
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-4">
        {/* Language selector UI */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsLangOpen(!isLangOpen)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-slate-50 border border-slate-200/90 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <Globe className="h-3.5 w-3.5 text-healthcare-600" />
            <span className="hidden sm:inline">{currentLang.nativeName || currentLang.label}</span>
            <ChevronDown className="h-3 w-3 text-slate-400" />
          </button>

          {isLangOpen && (
            <div className="absolute right-0 mt-1 w-44 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-50">
              <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                {t('selectLanguage', 'Select Language')}
              </div>
              {LANGUAGES.map((lang) => (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => {
                    setLanguage(lang.code as LanguageCode);
                    updateLanguage(lang.code);
                    setIsLangOpen(false);
                  }}
                  className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${
                    lang.code === language
                      ? 'bg-healthcare-50 font-semibold text-healthcare-800'
                      : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <span className="font-medium">{lang.nativeName}</span>{' '}
                  <span className="text-slate-400 text-[11px]">({lang.label})</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Notification visual bell icon */}
        <div className="relative">
          <button
            type="button"
            className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-50 transition-colors relative"
            title={t('notificationsDemo', 'Notifications (UI demonstration element)')}
          >
            <Bell className="h-4 w-4" />
            <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-healthcare-500 ring-2 ring-white" />
          </button>
        </div>

        {/* User Profile dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            className="flex items-center gap-2.5 pl-2 py-1 rounded-lg hover:bg-slate-50 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-healthcare-100 text-healthcare-800 font-bold flex items-center justify-center text-xs">
              {user?.name ? user.name.slice(0, 2).toUpperCase() : 'CB'}
            </div>
            <div className="text-left hidden lg:block">
              <div className="text-xs font-semibold text-slate-800 leading-tight">
                {user?.name || t('registeredPatient', 'Registered Patient')}
              </div>
              <div className="text-[11px] text-slate-500 leading-tight">
                {patient?.village?.name || t('ruralCommunity', 'Rural Community')}
              </div>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-slate-400 hidden sm:block" />
          </button>

          {isProfileOpen && (
            <div className="absolute right-0 mt-1 w-48 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-50">
              <div className="px-3 py-2 border-b border-slate-100">
                <div className="text-xs font-semibold text-slate-800">{user?.name}</div>
                <div className="text-[11px] text-slate-500">{user?.phone}</div>
                <div className="text-[10px] text-emerald-600 font-medium mt-0.5">
                  {t('roleLabel', 'Role:')} {user?.role || t('rolePatient', 'Patient')}
                </div>
              </div>

              <Link
                to="/profile"
                onClick={() => setIsProfileOpen(false)}
                className="flex items-center gap-2 px-3 py-2 text-xs text-slate-700 hover:bg-slate-50"
              >
                <UserCircle2 className="h-4 w-4 text-slate-400" />
                <span>{t('navProfile', 'My Profile')}</span>
              </Link>

              <button
                type="button"
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-rose-600 hover:bg-rose-50 border-t border-slate-100"
              >
                <LogOut className="h-4 w-4 text-rose-500" />
                <span>{t('signOut', 'Sign Out')}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
