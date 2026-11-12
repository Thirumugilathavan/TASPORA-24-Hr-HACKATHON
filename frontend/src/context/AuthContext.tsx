import React, { createContext, useContext, useState, useEffect } from 'react';
import { Patient, User } from '../types';
import { MOCK_PATIENT, MOCK_USER } from '../mocks/data';
import { authService, cleanPhoneNumber } from '../services/authService';
import { patientService } from '../services/patientService';
import { config } from '../lib/config';

interface AuthContextType {
  user: User | null;
  patient: Patient | null;
  currentPatient: Patient | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (phone: string, pass: string) => Promise<void>;
  register: (
    name: string,
    phone: string,
    pass: string,
    villageId: string,
    dob: string,
    lang: string,
    emergencyPhone?: string,
    consentGiven?: boolean
  ) => Promise<void>;
  loginDemoUser: () => void;
  logout: () => void;
  updateLanguage: (lang: string) => void;
  setPreferredLanguage: (lang: string) => void;
  refreshPatient: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const initAuth = async () => {
    const token = localStorage.getItem('carebridge_token');
    const storedUser = localStorage.getItem('carebridge_user');
    const storedPatient = localStorage.getItem('carebridge_patient');

    if (token && storedUser) {
      try {
        const parsedUser: User = JSON.parse(storedUser);
        setUser(parsedUser);

        if (storedPatient) {
          try {
            setPatient(JSON.parse(storedPatient));
          } catch {
            setPatient(null);
          }
        }

        // Attempt to fetch fresh patient record from API if online
        if (!config.isMockMode && parsedUser.id) {
          try {
            const freshPatient = await patientService.getPatient(parsedUser.id);
            if (freshPatient) {
              setPatient(freshPatient);
              localStorage.setItem('carebridge_patient', JSON.stringify(freshPatient));
            }
          } catch {
            // Keep stored patient
          }
        }
      } catch {
        authService.logout();
        setUser(null);
        setPatient(null);
      }
    } else {
      // Clean state for unauthenticated visitor
      setUser(null);
      setPatient(null);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    initAuth();
  }, []);

  const login = async (phone: string, pass: string) => {
    setIsLoading(true);
    try {
      const cleanPhone = cleanPhoneNumber(phone) || phone.trim();
      const loginRes = await authService.login({ phone: cleanPhone, password: pass });
      const loggedUser: User = {
        id: loginRes.user_id,
        name: cleanPhone,
        phone: cleanPhone,
        role: loginRes.role,
      };
      setUser(loggedUser);
      localStorage.setItem('carebridge_user', JSON.stringify(loggedUser));

      // Resolve patient profile using user_id
      try {
        const patientData = await patientService.getPatient(loginRes.user_id);
        if (patientData) {
          // If patient profile returns full name, update user object
          if (patientData.name) {
            loggedUser.name = patientData.name;
            localStorage.setItem('carebridge_user', JSON.stringify(loggedUser));
            setUser({ ...loggedUser });
          }
          setPatient(patientData);
          localStorage.setItem('carebridge_patient', JSON.stringify(patientData));
        }
      } catch (err) {
        console.warn('Patient profile not yet established for user:', err);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (
    name: string,
    phone: string,
    pass: string,
    villageId: string,
    dob: string,
    lang: string,
    emergencyPhone?: string,
    consentGiven: boolean = false
  ) => {
    setIsLoading(true);
    try {
      const cleanPhone = cleanPhoneNumber(phone) || phone.trim();
      // 1. Create auth user in backend
      const regRes = await authService.register({
        name,
        phone: cleanPhone,
        password: pass,
        role: 'PATIENT',
      });

      // 2. Obtain JWT credentials
      const loginRes = await authService.login({ phone: cleanPhone, password: pass });
      const newUser: User = {
        id: regRes.id || loginRes.user_id,
        name: regRes.name || name,
        phone: regRes.phone || cleanPhone,
        role: regRes.role || 'PATIENT',
      };
      setUser(newUser);
      localStorage.setItem('carebridge_user', JSON.stringify(newUser));

      // 3. Establish canonical Patient profile linked to village
      await patientService.createPatient({
        village_id: villageId,
        date_of_birth: dob,
        preferred_language: lang,
        consent_given: consentGiven === true,
        emergency_contact_phone: emergencyPhone,
      });

      // 4. Retrieve complete patient record with resolved village & coordinates
      try {
        const fullPatient = await patientService.getPatient(newUser.id);
        if (fullPatient) {
          setPatient(fullPatient);
          localStorage.setItem('carebridge_patient', JSON.stringify(fullPatient));
        }
      } catch (err) {
        console.warn('Could not immediately fetch full patient profile:', err);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const loginDemoUser = async () => {
    setIsLoading(true);
    try {
      await login('9876543210', 'DemoPass123!');
    } catch (e) {
      console.warn('Backend login for demo user failed, using local profile:', e);
      setUser(MOCK_USER);
      setPatient(MOCK_PATIENT);
      localStorage.setItem('carebridge_user', JSON.stringify(MOCK_USER));
      localStorage.setItem('carebridge_patient', JSON.stringify(MOCK_PATIENT));
      localStorage.setItem('carebridge_token', 'demo-patient-token-session');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    authService.logout();
    setUser(null);
    setPatient(null);
  };

  const updateLanguage = (lang: string) => {
    if (patient) {
      const updated = { ...patient, preferred_language: lang };
      setPatient(updated);
      localStorage.setItem('carebridge_patient', JSON.stringify(updated));
    }
    localStorage.setItem('carebridge_language', lang);
  };

  const refreshPatient = async () => {
    if (user?.id) {
      try {
        const fresh = await patientService.getPatient(user.id);
        if (fresh) {
          setPatient(fresh);
          localStorage.setItem('carebridge_patient', JSON.stringify(fresh));
        }
      } catch (err) {
        console.error('Failed to refresh patient profile:', err);
      }
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        patient,
        currentPatient: patient,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        loginDemoUser,
        logout,
        updateLanguage,
        setPreferredLanguage: updateLanguage,
        refreshPatient,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
