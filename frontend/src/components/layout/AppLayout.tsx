import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Bot } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { DemoBanner } from '../common/DemoBanner';
import { EmergencyNotice } from '../common/EmergencyNotice';
import { ToastContainer } from '../common/Toast';
import { AIAssistantModal } from '../assistant/AIAssistantModal';
import { useTranslation } from '../../context/LanguageContext';

export const AppLayout: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isAIAssistantOpen, setIsAIAssistantOpen] = useState(false);
  const { language } = useTranslation();
  const location = useLocation();

  // Map route to human-readable page titles and breadcrumbs
  const getPageMeta = () => {
    switch (location.pathname) {
      case '/':
        return { title: 'Patient Overview', breadcrumb: 'Dashboard' };
      case '/facilities':
        return { title: 'Find Healthcare Facilities', breadcrumb: 'Healthcare Directory' };
      case '/medicines':
        return { title: 'Medicine Stock & Availability', breadcrumb: 'Pharmacy & Supplies' };
      case '/requests':
        return { title: 'My Healthcare Requests', breadcrumb: 'Care Coordination' };
      case '/appointments':
        return { title: 'Scheduled Appointments', breadcrumb: 'Consultations' };
      case '/profile':
        return { title: 'Patient Profile & Preferences', breadcrumb: 'Account' };
      default:
        return { title: 'CareBridge', breadcrumb: 'Portal' };
    }
  };

  const { title, breadcrumb } = getPageMeta();

  React.useEffect(() => {
    const handleOpenAI = () => setIsAIAssistantOpen(true);
    window.addEventListener('open-carebridge-ai', handleOpenAI);
    return () => window.removeEventListener('open-carebridge-ai', handleOpenAI);
  }, []);

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

      {/* Floating AI Assistant Action Button */}
      <button
        type="button"
        onClick={() => setIsAIAssistantOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2.5 px-4 py-2.5 bg-gradient-to-r from-teal-700 via-teal-800 to-navy-900 text-white rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all border border-teal-500/30 group cursor-pointer"
        aria-label="Open CareBridge AI Assistant"
      >
        <div className="w-6 h-6 rounded-full bg-teal-500/20 flex items-center justify-center border border-teal-400/30">
          <Bot className="w-4 h-4 text-teal-200 group-hover:rotate-12 transition-transform" />
        </div>
        <span className="font-semibold text-xs tracking-wide">
          {language === 'ta' ? 'AI உதவியாளர்' : 'CareBridge AI'}
        </span>
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
      </button>

      {/* AI Assistant Modal */}
      <AIAssistantModal
        isOpen={isAIAssistantOpen}
        onClose={() => setIsAIAssistantOpen(false)}
      />

      {/* Global Toast Feedback */}
      <ToastContainer />
    </div>
  );
};
