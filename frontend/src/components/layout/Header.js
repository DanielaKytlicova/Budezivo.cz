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
    <header className="bg-white border-b border-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center space-x-2">
          <h1 className="text-2xl font-bold text-primary">KulturaBooking</h1>
        </Link>

        <div className="flex items-center space-x-4">
          <button
            data-testid="language-switcher"
            onClick={() => switchLanguage(language === 'cs' ? 'en' : 'cs')}
            className="flex items-center space-x-1 text-sm text-muted-foreground hover:text-primary transition-colors"
          >
            <Globe className="w-4 h-4" />
            <span>{language === 'cs' ? 'EN' : 'CS'}</span>
          </button>

          {user ? (
            <>
              <Link to="/admin" data-testid="admin-dashboard-link">
                <Button variant="ghost" size="sm">{t('nav.dashboard')}</Button>
              </Link>
              <Button
                data-testid="logout-button"
                variant="ghost"
                size="sm"
                onClick={logout}
              >
                <LogOut className="w-4 h-4 mr-2" />
                {t('nav.logout')}
              </Button>
            </>
          ) : (
            <>
              <Link to="/login" data-testid="login-link">
                <Button variant="ghost" size="sm">{t('nav.login')}</Button>
              </Link>
              <Link to="/register" data-testid="register-link">
                <Button size="sm" className="bg-[var(--theme-accent)] text-primary hover:bg-[var(--theme-accent)]/90">
                  {t('nav.register')}
                </Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
