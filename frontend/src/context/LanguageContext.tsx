import React, { createContext, useContext, useState, useEffect } from 'react';
import { LanguageCode, getTranslation } from '../lib/i18n';

interface LanguageContextType {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  t: (key: string, fallbackOrParams?: string | Record<string, string | number>, params?: Record<string, string | number>) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<LanguageCode>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('nalam_language') || localStorage.getItem('carebridge_language');
      if (stored && (stored === 'en' || stored === 'ta' || stored === 'hi' || stored === 'te' || stored === 'bn')) {
        return stored as LanguageCode;
      }
    }
    return 'ta'; // Tamil default for NALAM Tamil Nadu platform context
  });

  const setLanguage = (lang: LanguageCode) => {
    setLanguageState(lang);
    if (typeof window !== 'undefined') {
      localStorage.setItem('nalam_language', lang);
      localStorage.setItem('carebridge_language', lang);
    }
  };

  const t = (key: string, fallbackOrParams?: string | Record<string, string | number>, params?: Record<string, string | number>) => {
    const fallback = typeof fallbackOrParams === 'string' ? fallbackOrParams : undefined;
    const interpolations = typeof fallbackOrParams === 'object' ? fallbackOrParams : params;
    let result = getTranslation(language, key, fallback);
    if (interpolations) {
      Object.entries(interpolations).forEach(([k, v]) => {
        result = result.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
        result = result.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
      });
    }
    return result;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useTranslation = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useTranslation must be used within a LanguageProvider');
  }
  return context;
};
