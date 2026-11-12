import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Hospital,
  Pill,
  ClipboardList,
  CalendarCheck,
  User,
  HeartHandshake,
  X,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useTranslation } from '../../context/LanguageContext';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();

  const navItems = [
    { to: '/', label: t('navDashboard', 'Dashboard'), icon: LayoutDashboard },
    { to: '/facilities', label: t('navFacilities', 'Find Healthcare'), icon: Hospital },
    { to: '/medicines', label: t('navMedicines', 'Medicine Availability'), icon: Pill },
    { to: '/requests', label: t('navRequests', 'My Requests'), icon: ClipboardList },
    { to: '/appointments', label: t('navAppointments', 'Appointments'), icon: CalendarCheck },
    { to: '/profile', label: t('navProfile', 'Profile'), icon: User },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-navy-950/50 backdrop-blur-xs md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar container */}
      <aside
        className={cn(
          'fixed top-0 bottom-0 left-0 z-40 w-64 bg-white border-r border-slate-200/90 flex flex-col transition-transform duration-200 ease-in-out md:translate-x-0 md:static',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Brand Header */}
        <div className="flex items-center justify-between h-16 px-5 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-healthcare-600 text-white shadow-sm">
              <HeartHandshake className="h-5 w-5" />
            </div>
            <div>
              <span className="text-lg font-bold text-navy-900 tracking-tight">CareBridge</span>
              <span className="block text-[10px] uppercase font-semibold text-healthcare-700 tracking-wider">
                Rural Healthcare
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="md:hidden p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation list */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-healthcare-50 text-healthcare-800 font-semibold shadow-xs'
                    : 'text-slate-600 hover:text-navy-900 hover:bg-slate-50'
                )
              }
            >
              <item.icon className="h-4 w-4 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer info / Assistance */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/70 m-3 rounded-xl text-xs text-slate-500">
          <p className="font-semibold text-slate-700">{t('tagline', 'No Wasted Trips. Better Access.')}</p>
          <p className="mt-0.5 text-[11px] leading-relaxed">
            Contact your local ASHA worker or village health representative for in-person support.
          </p>
        </div>
      </aside>
    </>
  );
};
