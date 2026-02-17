import React, { useContext } from 'react';
import { Link } from 'react-router-dom';
import { AuthContext } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { LogOut } from 'lucide-react';

// Minimalistické logo Budeživo.cz - název + check-in ikona
const BudezivoLogo = ({ showText = true, className = "" }) => (
  <div className={`flex items-center gap-2 ${className}`}>
    {/* Check-in ikona */}
    <div className="w-8 h-8 rounded-lg bg-[#4A6FA5] flex items-center justify-center">
      <svg 
        width="18" 
        height="18" 
        viewBox="0 0 24 24" 
        fill="none" 
        stroke="white" 
        strokeWidth="2.5" 
        strokeLinecap="round" 
        strokeLinejoin="round"
      >
        <polyline points="20 6 9 17 4 12" />
      </svg>
    </div>
    {/* Název */}
    {showText && (
      <span className="font-bold text-[#4A6FA5] text-xl tracking-tight">
        Budeživo<span className="text-[#C4AB86]">.cz</span>
      </span>
    )}
  </div>
);

export const Header = ({ minimal = false }) => {
  const { user, logout } = useContext(AuthContext);

  // Detekce mobilní verze
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center" data-testid="logo-link">
          {/* Na mobilu při přihlášení/správě zobrazit pouze ikonu */}
          <div className="md:hidden">
            <BubezivoLogo showText={!minimal} />
          </div>
          {/* Na desktopu vždy plné logo */}
          <div className="hidden md:block">
            <BubezivoLogo showText={true} />
          </div>
        </Link>

        {/* Navigace - pouze na desktopu a na homepage */}
        {!minimal && (
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
        )}

        <div className="flex items-center space-x-4">
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
            /* Tlačítko "Vyzkoušet zdarma" - pouze na desktopu */
            <Link to="/register" data-testid="register-link" className="hidden md:block">
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

// Export loga pro použití jinde
export { BubezivoLogo };
