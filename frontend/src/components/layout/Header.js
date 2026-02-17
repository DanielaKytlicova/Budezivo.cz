import React, { useContext } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from '../../i18n/useTranslation';
import { LanguageContext } from '../../context/LanguageContext';
import { AuthContext } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Globe, LogOut } from 'lucide-react';

export const Header = () => {
  const { t } = useTranslation();
  const { language, switchLanguage } = useContext(LanguageContext);
  const { user, logout } = useContext(AuthContext);

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 md:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center">
          <h1 className="text-xl font-semibold text-[#4A6FA5]">RezervačníSystém</h1>
        </Link>

        <nav className="hidden md:flex items-center space-x-8">
          <a href="#funkce" className="text-[#4A6FA5] text-sm font-medium hover:text-[#3d5c89] transition-colors">
            Funkce
          </a>
          <a href="#pricing" className="text-[#4A6FA5] text-sm font-medium hover:text-[#3d5c89] transition-colors">
            Tarify
          </a>
          <a href="#faq" className="text-[#4A6FA5] text-sm font-medium hover:text-[#3d5c89] transition-colors">
            FAQ
          </a>
          {!user && (
            <Link to="/login" className="text-[#4A6FA5] text-sm font-medium hover:text-[#3d5c89] transition-colors">
              Přihlášení
            </Link>
          )}
        </nav>

        <div className="flex items-center space-x-4">
          <button
            data-testid="language-switcher"
            onClick={() => switchLanguage(language === 'cs' ? 'en' : 'cs')}
            className="flex items-center space-x-1 text-sm text-gray-600 hover:text-[#4A6FA5] transition-colors"
          >
            <Globe className="w-4 h-4" />
            <span>{language === 'cs' ? 'EN' : 'CS'}</span>
          </button>

          {user ? (
            <>
              <Link to="/admin" data-testid="admin-dashboard-link">
                <Button variant="ghost" size="sm" className="text-[#4A6FA5]">
                  {t('nav.dashboard')}
                </Button>
              </Link>
              <Button
                data-testid="logout-button"
                variant="ghost"
                size="sm"
                onClick={logout}
                className="text-[#4A6FA5]"
              >
                <LogOut className="w-4 h-4 mr-2" />
                {t('nav.logout')}
              </Button>
            </>
          ) : (
            <Link to="/register" data-testid="register-link">
              <Button 
                size="sm" 
                className="bg-[#C4AB86] text-white hover:bg-[#b39975] rounded-lg px-6 h-10"
              >
                Vyzkoušet zdarma
              </Button>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};
