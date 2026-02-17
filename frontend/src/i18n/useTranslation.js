import { useContext } from 'react';
import { LanguageContext } from '../context/LanguageContext';
import cs from './cs.json';
import en from './en.json';

const translations = { cs, en };

export const useTranslation = () => {
  const { language } = useContext(LanguageContext);

  const t = (key) => {
    const keys = key.split('.');
    let value = translations[language];

    for (const k of keys) {
      if (value && typeof value === 'object') {
        value = value[k];
      } else {
        return key;
      }
    }

    return value || key;
  };

  return { t, language };
};
