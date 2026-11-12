import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { useAuth } from './context/AuthContext';
import { LoadingState } from './components/common/LoadingState';

// Pages
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { FacilitiesPage } from './pages/FacilitiesPage';
import { MedicinesPage } from './pages/MedicinesPage';
import { RequestsPage } from './pages/RequestsPage';
import { AppointmentsPage } from './pages/AppointmentsPage';
import { ProfilePage } from './pages/ProfilePage';
import { IVRPage } from './pages/IVRPage';
import { CampsPage } from './pages/CampsPage';

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <LoadingState message="Initializing NALAM AI platform..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <Routes>
      {/* Public Authentication Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Public Zero-Cost Telephone IVR Helpline Simulation Route */}
      <Route path="/ivr" element={<IVRPage />} />

      {/* Protected Portal Routes wrapped in AppLayout */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="facilities" element={<FacilitiesPage />} />
        <Route path="medicines" element={<MedicinesPage />} />
        <Route path="requests" element={<RequestsPage />} />
        <Route path="appointments" element={<AppointmentsPage />} />
        <Route path="camps" element={<CampsPage />} />
        <Route path="profile" element={<ProfilePage />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
