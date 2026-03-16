import React from 'react';
import { Link } from 'react-router-dom';

/**
 * BookingHeader - Header komponenta pro veřejné booking stránky
 * 
 * Zobrazuje logo instituce (pokud je k dispozici) místo loga Budeživo.cz
 * Aplikuje theme barvy instituce na header
 * 
 * Funkce "vlastní logo" a "vlastní theme" jsou připraveny jako PRO feature,
 * ale momentálně jsou dostupné pro všechny registrované instituce.
 * 
 * Pro aktivaci PRO-only režimu změňte konstanty na false
 */

// Konfigurace PRO funkcí - true = dostupné pro všechny, false = pouze PRO
const CUSTOM_LOGO_FREE_FOR_ALL = true;
const CUSTOM_THEME_FREE_FOR_ALL = true;

// Výchozí logo Budeživo.cz
const BudezivoLogo = ({ primaryColor = '#4A6FA5', className = "" }) => (
  <div className={`flex items-center gap-2 ${className}`}>
    <div 
      className="w-8 h-8 rounded-lg flex items-center justify-center"
      style={{ backgroundColor: primaryColor }}
    >
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
    <span className="font-bold text-xl tracking-tight" style={{ color: primaryColor }}>
      Budeživo<span className="text-[#C4AB86]">.cz</span>
    </span>
  </div>
);

// Logo instituce
const InstitutionLogo = ({ logoUrl, institutionName, onError }) => (
  <div className="flex items-center gap-3">
    <img 
      src={logoUrl} 
      alt={institutionName || 'Logo instituce'} 
      className="h-10 max-w-[180px] object-contain"
      onError={onError}
      data-testid="institution-logo-img"
    />
  </div>
);

/**
 * BookingHeader Component
 * 
 * @param {Object} props
 * @param {string} props.logoUrl - URL loga instituce
 * @param {string} props.institutionName - Název instituce
 * @param {string} props.primaryColor - Primární barva instituce
 * @param {string} props.secondaryColor - Sekundární barva instituce
 * @param {string} props.accentColor - Akcentová barva instituce
 * @param {string} props.headerStyle - Styl headeru ('light' | 'dark')
 * @param {string} props.plan - Tarif instituce ('free', 'pro', 'enterprise')
 * @param {string} props.institutionId - ID instituce pro odkaz
 */
export const BookingHeader = ({ 
  logoUrl, 
  institutionName, 
  primaryColor = '#4A6FA5',
  secondaryColor = '#84A98C',
  accentColor = '#E9C46A',
  headerStyle = 'light',
  plan = 'free',
  institutionId
}) => {
  const [logoError, setLogoError] = React.useState(false);
  
  // Rozhodnout, zda zobrazit vlastní logo/theme
  const canShowCustomLogo = CUSTOM_LOGO_FREE_FOR_ALL || ['pro', 'enterprise'].includes(plan);
  const canShowCustomTheme = CUSTOM_THEME_FREE_FOR_ALL || ['pro', 'enterprise'].includes(plan);
  
  const showInstitutionLogo = canShowCustomLogo && logoUrl && !logoError;
  
  // Určit barvy podle theme
  const effectivePrimaryColor = canShowCustomTheme ? primaryColor : '#4A6FA5';
  const isDarkHeader = headerStyle === 'dark';
  
  // Barvy headeru
  const headerBgColor = isDarkHeader ? effectivePrimaryColor : '#ffffff';
  const headerTextColor = isDarkHeader ? '#ffffff' : effectivePrimaryColor;
  const borderColor = isDarkHeader ? 'transparent' : '#e5e7eb';

  const handleLogoError = () => {
    setLogoError(true);
  };

  return (
    <header 
      className="sticky top-0 z-50 border-b"
      style={{ 
        backgroundColor: headerBgColor,
        borderColor: borderColor
      }}
      data-testid="booking-header"
    >
      <div className="max-w-7xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
        {/* Logo - vlevo */}
        <Link 
          to={institutionId ? `/booking/${institutionId}` : '/'} 
          className="flex items-center"
          data-testid="booking-header-logo"
        >
          {showInstitutionLogo ? (
            <InstitutionLogo 
              logoUrl={logoUrl} 
              institutionName={institutionName}
              onError={handleLogoError}
            />
          ) : (
            <BudezivoLogo primaryColor={effectivePrimaryColor} />
          )}
        </Link>

        {/* Název instituce - střed (pouze pokud je vlastní logo) */}
        {showInstitutionLogo && institutionName && (
          <div className="hidden md:block flex-1 text-center">
            <span 
              className="text-sm font-medium"
              style={{ color: headerTextColor }}
              data-testid="institution-name"
            >
              {institutionName}
            </span>
          </div>
        )}

        {/* Powered by badge - vpravo (pouze pokud je vlastní logo) */}
        {showInstitutionLogo && (
          <a 
            href="https://budezivo.cz" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-xs transition-colors hidden sm:block"
            style={{ 
              color: isDarkHeader ? 'rgba(255,255,255,0.6)' : '#9ca3af'
            }}
            data-testid="powered-by-link"
          >
            Powered by <span className="font-medium">Budeživo.cz</span>
          </a>
        )}
      </div>
    </header>
  );
};

export default BookingHeader;
