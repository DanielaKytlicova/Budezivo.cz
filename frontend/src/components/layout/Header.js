import React, { useContext } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { AuthContext } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { LogOut } from 'lucide-react';

// Logo Budeživo.cz - oficiální SVG
const BudezivoLogo = ({ showText = true, className = "" }) => (
  <div className={`flex items-center ${className}`}>
    {showText ? (
      /* Plné logo s názvem */
      <svg 
        viewBox="0 0 265.42 73.09" 
        className="h-8 w-auto"
        aria-label="Budeživo.cz"
      >
        <defs>
          <style>{`.logo-blue{fill:#5a7aae;}.logo-gold{fill:#c5ac87;}`}</style>
        </defs>
        <path className="logo-blue" d="M41.23,40.83a5.17,5.17,0,0,0-2.42-.69V39.9a5.64,5.64,0,0,0,2.1-.88,4.54,4.54,0,0,0,1.43-1.62,4.61,4.61,0,0,0,.52-2.22A5,5,0,0,0,42,32.29a5.43,5.43,0,0,0-2.48-1.94,10.42,10.42,0,0,0-4.09-.7h-9V51.48h9.73a9.64,9.64,0,0,0,4.12-.8,6,6,0,0,0,2.57-2.16,5.69,5.69,0,0,0,.88-3.14A5.26,5.26,0,0,0,43,42.64,5,5,0,0,0,41.23,40.83Zm-9.65-7h3.09a3.28,3.28,0,0,1,2.13.64,2.13,2.13,0,0,1,.79,1.75,2.28,2.28,0,0,1-.39,1.34,2.58,2.58,0,0,1-1.07.84,4,4,0,0,1-1.54.29h-3Zm5.91,12.85a4,4,0,0,1-2.57.67H31.58V42H35a4.12,4.12,0,0,1,1.76.34,2.67,2.67,0,0,1,1.14,1,2.75,2.75,0,0,1,.39,1.48A2.22,2.22,0,0,1,37.49,46.63Z"/>
        <path className="logo-blue" d="M56.91,44.44a3.48,3.48,0,0,1-.35,1.64,2.5,2.5,0,0,1-1,1,2.91,2.91,0,0,1-1.47.36,2.51,2.51,0,0,1-2-.79,3.06,3.06,0,0,1-.71-2.16V35.1H46.34V45.53a7.09,7.09,0,0,0,.7,3.24,5.21,5.21,0,0,0,2,2.15,5.77,5.77,0,0,0,3,.76,4.82,4.82,0,0,0,3.43-1.19,6.67,6.67,0,0,0,1.69-2.59l.08,3.58H62V35.1H56.91Z"/>
        <path className="logo-blue" d="M76.05,37.91h-.12a5.3,5.3,0,0,0-.9-1.44,4.65,4.65,0,0,0-1.52-1.13,5,5,0,0,0-2.22-.45,6.08,6.08,0,0,0-3.21.9,6.46,6.46,0,0,0-2.4,2.77,10.8,10.8,0,0,0-.91,4.74A10.81,10.81,0,0,0,65.65,48,6.4,6.4,0,0,0,68,50.77a6,6,0,0,0,3.31.94,5.07,5.07,0,0,0,2.16-.42A4.79,4.79,0,0,0,75,50.22a5.33,5.33,0,0,0,.93-1.4h.18v2.66h5V29.65h-5.1Zm-.25,7.72a3.54,3.54,0,0,1-1.06,1.55,2.66,2.66,0,0,1-1.67.55,2.59,2.59,0,0,1-1.66-.55,3.4,3.4,0,0,1-1-1.56A6.86,6.86,0,0,1,70,43.3,6.78,6.78,0,0,1,70.38,41a3.38,3.38,0,0,1,1-1.54,2.54,2.54,0,0,1,1.66-.55,2.65,2.65,0,0,1,1.67.54A3.33,3.33,0,0,1,75.8,41a7.78,7.78,0,0,1,0,4.68Z"/>
        <path className="logo-blue" d="M97.65,37a6.9,6.9,0,0,0-2.51-1.61A9,9,0,0,0,92,34.89,8.44,8.44,0,0,0,87.69,36a7.23,7.23,0,0,0-2.8,3,9.44,9.44,0,0,0-1,4.42,9.63,9.63,0,0,0,1,4.52,6.9,6.9,0,0,0,2.85,2.91,9.16,9.16,0,0,0,4.42,1,10.13,10.13,0,0,0,3.53-.57,6.65,6.65,0,0,0,2.53-1.62,5.8,5.8,0,0,0,1.41-2.45l-4.55-.75a2.55,2.55,0,0,1-.61.93,2.68,2.68,0,0,1-1,.57,4,4,0,0,1-1.25.19,3.5,3.5,0,0,1-1.74-.42,2.87,2.87,0,0,1-1.17-1.26A4.54,4.54,0,0,1,89,44.53H99.87V43.24a10.16,10.16,0,0,0-.58-3.59A7.26,7.26,0,0,0,97.65,37ZM89,41.56a4.46,4.46,0,0,1,.3-1.27,2.87,2.87,0,0,1,1-1.25A3.1,3.1,0,0,1,92,38.6a3,3,0,0,1,1.67.44,2.74,2.74,0,0,1,1,1.26A4.67,4.67,0,0,1,95,41.56Z"/>
        <path className="logo-blue" d="M200.58,46.32a2.71,2.71,0,0,0-2,.78,2.78,2.78,0,0,0,0,3.9,2.88,2.88,0,0,0,3.94,0,2.78,2.78,0,0,0,0-3.9A2.71,2.71,0,0,0,200.58,46.32Z"/>
        <path className="logo-blue" d="M217.66,46.27a3.33,3.33,0,0,1-.6.88,2.44,2.44,0,0,1-.82.54,2.73,2.73,0,0,1-1,.18,2.56,2.56,0,0,1-1.67-.55,3.35,3.35,0,0,1-1.05-1.57,7.4,7.4,0,0,1-.36-2.43,7.32,7.32,0,0,1,.36-2.43,3.24,3.24,0,0,1,1.05-1.55,2.61,2.61,0,0,1,1.67-.54,2.8,2.8,0,0,1,1,.18,2.24,2.24,0,0,1,.8.53,3,3,0,0,1,.59.85A4.49,4.49,0,0,1,218,41.5l4.71-.79a6.6,6.6,0,0,0-.8-2.41,5.82,5.82,0,0,0-1.59-1.83A7.23,7.23,0,0,0,218,35.3a9.66,9.66,0,0,0-2.87-.41A8.78,8.78,0,0,0,210.75,36a7.23,7.23,0,0,0-2.84,3,10.38,10.38,0,0,0,0,8.85,7.17,7.17,0,0,0,2.84,3,8.67,8.67,0,0,0,4.41,1.06,9.46,9.46,0,0,0,2.88-.41,7.1,7.1,0,0,0,2.29-1.18,6.36,6.36,0,0,0,1.59-1.87,7.18,7.18,0,0,0,.8-2.47L218,45.09A4.53,4.53,0,0,1,217.66,46.27Z"/>
        <polygon className="logo-blue" points="231.66 47.48 231.66 47.37 238.73 38.33 238.73 35.1 225.25 35.1 225.25 39.1 232.64 39.1 232.64 39.2 225 48.53 225 51.48 239.01 51.48 239.01 47.48 231.66 47.48"/>
        <path className="logo-blue" d="M181.38,19.53h-35.8l-4.43,5h40.23A4.26,4.26,0,0,1,185.43,29v23.9a4.26,4.26,0,0,1-4.05,4.44H116a4.26,4.26,0,0,1-4-4.44V29a4.26,4.26,0,0,1,4-4.44h11.55l3.61-5H116A9.26,9.26,0,0,0,107,29v23.9a9.27,9.27,0,0,0,9,9.44h65.38a9.27,9.27,0,0,0,9.05-9.44V29A9.26,9.26,0,0,0,181.38,19.53Z"/>
        <polygon className="logo-gold" points="119.77 48.53 119.77 51.48 133.78 51.48 133.78 47.48 126.42 47.48 126.42 47.37 133.5 38.33 133.5 35.1 120.02 35.1 120.02 39.1 127.41 39.1 127.41 39.2 119.77 48.53"/>
        <path className="logo-gold" d="M141.6,29a2.66,2.66,0,0,0-1.87-.72,2.61,2.61,0,0,0-1.86.72,2.33,2.33,0,0,0,0,3.48,2.58,2.58,0,0,0,1.86.73,2.66,2.66,0,0,0,1.87-.72,2.28,2.28,0,0,0,.78-1.73A2.31,2.31,0,0,0,141.6,29Z"/>
        <rect className="logo-gold" x="137.18" y="35.1" width="5.11" height="16.38"/>
        <path className="logo-gold" d="M162.13,35.1h-5.34l-2.4,8c-.32,1.08-.6,2.19-.84,3.3-.09.41-.18.84-.26,1.27-.09-.43-.19-.86-.28-1.27-.24-1.13-.53-2.23-.86-3.3l-2.45-8h-5.39l5.94,16.38h5.91Z"/>
        <path className="logo-gold" d="M166.74,50.72a9.7,9.7,0,0,0,8.82,0,7.08,7.08,0,0,0,2.83-3,10.48,10.48,0,0,0,0-8.85,7.14,7.14,0,0,0-2.83-3,9.7,9.7,0,0,0-8.82,0,7.21,7.21,0,0,0-2.83,3,10.38,10.38,0,0,0,0,8.85A7.15,7.15,0,0,0,166.74,50.72Zm1.74-9.79a3.41,3.41,0,0,1,1-1.57,2.73,2.73,0,0,1,3.31,0,3.41,3.41,0,0,1,1,1.57,8.54,8.54,0,0,1,0,4.77,3.46,3.46,0,0,1-1,1.6,2.69,2.69,0,0,1-3.31,0,3.46,3.46,0,0,1-1-1.6,8.3,8.3,0,0,1,0-4.77Z"/>
        <polygon className="logo-gold" points="126.8 30.85 124.7 28.39 120.38 28.39 120.38 28.39 120.38 28.48 120.38 28.48 124.94 32.99 128.64 32.99 133.2 28.48 136.69 24.53 141.12 19.53 148.87 10.78 141.58 10.78 135.27 19.53 131.66 24.53 128.88 28.39 126.8 30.85"/>
      </svg>
    ) : (
      /* Pouze ikona - kompaktní verze */
      <svg 
        viewBox="0 0 73.42 73.09" 
        className="h-8 w-8"
        aria-label="Budeživo.cz"
      >
        <defs>
          <style>{`.logo-icon-blue{fill:#5a7aae;}.logo-icon-gold{fill:#c5ac87;}`}</style>
        </defs>
        <path className="logo-icon-blue" d="M46.9,55A1.87,1.87,0,0,1,45,56.84H14.88A1.87,1.87,0,0,1,13,55V24.83A1.87,1.87,0,0,1,14.88,23H37.74l6.43-8.91H14.88A10.79,10.79,0,0,0,4.11,24.83V55A10.78,10.78,0,0,0,14.88,65.74H45A10.78,10.78,0,0,0,55.8,55V31.55L46.9,41.6Z"/>
        <polygon className="logo-icon-gold" points="30.01 43.07 26.28 38.69 18.58 38.69 18.58 38.85 26.7 46.88 33.3 46.88 41.41 38.85 46.9 32.65 55.6 22.83 69.31 7.35 56.32 7.35 50.41 15.55 45.06 22.96 33.71 38.69 30.01 43.07"/>
      </svg>
    )}
  </div>
);

export const Header = ({ minimal = false }) => {
  const { user, logout } = useContext(AuthContext);
  const location = useLocation();

  // Stránky kde se zobrazí tlačítko "Vyzkoušet zdarma" a "Přihlášení"
  const publicPages = ['/', '/funkce', '/tarify', '/gdpr', '/kontakt'];
  const isPublicPage = publicPages.includes(location.pathname);

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center" data-testid="logo-link">
          {/* Na mobilu při přihlášení/správě zobrazit pouze ikonu */}
          <div className="md:hidden">
            <BudezivoLogo showText={!minimal} />
          </div>
          {/* Na desktopu vždy plné logo */}
          <div className="hidden md:block">
            <BudezivoLogo showText={true} />
          </div>
        </Link>

        {/* Navigace - pouze na veřejných stránkách */}
        {isPublicPage && !user && (
          <nav className="hidden md:flex items-center space-x-8">
            <a href="/#funkce" className="text-[#4A6FA5] text-sm font-medium hover:text-[#3d5c89] transition-colors">
              Funkce
            </a>
            <a href="/#pricing" className="text-[#4A6FA5] text-sm font-medium hover:text-[#3d5c89] transition-colors">
              Tarify
            </a>
            <a href="/#faq" className="text-[#4A6FA5] text-sm font-medium hover:text-[#3d5c89] transition-colors">
              FAQ
            </a>
            <Link to="/kontakt" className="text-[#4A6FA5] text-sm font-medium hover:text-[#3d5c89] transition-colors">
              Kontakt
            </Link>
          </nav>
        )}

        <div className="flex items-center space-x-2 md:space-x-4">
          {user ? (
            <>
              <Link to="/admin" data-testid="admin-dashboard-link">
                <Button variant="ghost" size="sm" className="text-[#4A6FA5] hidden md:inline-flex">
                  Přehled
                </Button>
              </Link>
              <Button
                data-testid="logout-button"
                variant="ghost"
                size="sm"
                onClick={logout}
                className="text-[#4A6FA5]"
              >
                <LogOut className="w-4 h-4 md:mr-2" />
                <span className="hidden md:inline">Odhlásit</span>
              </Button>
            </>
          ) : (
            /* Tlačítka pouze na veřejných stránkách */
            isPublicPage && (
              <>
                {/* Přihlášení - viditelné na mobilu i desktopu */}
                <Link to="/login" data-testid="login-link">
                  <Button 
                    variant="ghost"
                    size="sm" 
                    className="text-[#4A6FA5] hover:text-white hover:bg-[#4A6FA5] transition-colors"
                  >
                    Přihlášení
                  </Button>
                </Link>
                {/* Vyzkoušet zdarma - pouze desktop */}
                <Link to="/register" data-testid="register-link" className="hidden md:block mr-[5px]">
                  <Button 
                    size="sm" 
                    className="bg-[#C4AB86] text-white hover:bg-[#b39975] rounded-lg px-6 h-10"
                  >
                    Vyzkoušet zdarma
                  </Button>
                </Link>
              </>
            )
          )}
        </div>
      </div>
    </header>
  );
};

// Export loga pro použití jinde
export { BudezivoLogo };
