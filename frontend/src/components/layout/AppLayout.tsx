import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { DemoBanner } from '../common/DemoBanner';
import { EmergencyNotice } from '../common/EmergencyNotice';
import { ToastContainer } from '../common/Toast';
import { useTranslation } from '../../context/LanguageContext';

export const AppLayout: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const location = useLocation();
  const { t } = useTranslation();

  // Map route to human-readable page titles and breadcrumbs
  const getPageMeta = () => {
    switch (location.pathname) {
      case '/':
        return { title: t('appName', 'CareBridge'), breadcrumb: t('navDashboard', 'Dashboard') };
      case '/facilities':
        return { title: t('facilitiesTitle', 'Healthcare Facilities Directory'), breadcrumb: t('navFacilities', 'Find Healthcare') };
      case '/medicines':
        return { title: t('medicinesTitle', 'Essential Medicines & Inventory Availability'), breadcrumb: t('navMedicines', 'Medicine Stock') };
      case '/requests':
        return { title: t('requestsTitle', 'Healthcare Requests & AI Routing'), breadcrumb: t('navRequests', 'Healthcare Requests') };
      case '/appointments':
        return { title: t('appointmentsTitle', 'Scheduled Appointments'), breadcrumb: t('navAppointments', 'Appointments') };
      case '/profile':
        return { title: t('profileTitle', 'Patient Profile & Settings'), breadcrumb: t('navProfile', 'My Profile') };
      default:
        return { title: t('appName', 'CareBridge'), breadcrumb: t('ruralHealthcare', 'Rural Healthcare') };
    }
  };

  const { title, breadcrumb } = getPageMeta();

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Top Demo Banner indicating mock/live mode */}
      <DemoBanner />

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
          <Header
            onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
            title={title}
            breadcrumb={breadcrumb}
          />

          <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
            <Outlet />
          </main>

          {/* Bottom Medical Disclaimer */}
          <footer className="p-4 sm:px-6 lg:px-8 border-t border-slate-200/80 bg-white">
            <div className="max-w-7xl mx-auto">
              <EmergencyNotice />
            </div>
          </footer>
        </div>
      </div>

      {/* Global Toast Feedback */}
      <ToastContainer />
    </div>
  );
};
