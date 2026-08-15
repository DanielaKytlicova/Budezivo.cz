import React, { useContext, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { AuthContext } from '../../context/AuthContext';
import { ArrowRight, LogOut, Menu, X } from 'lucide-react';

const mainNav = [
  { label: 'O projektu', href: '/#o-projektu' },
  { label: 'Co systém umí', href: '/#moznosti' },
  { label: 'Ceník', href: '/#cenik-nabidky' },
  { label: 'Kontakt', href: '/kontakt' },
];

const publicPages = new Set([
  '/',
  '/kontakt',
  '/gdpr',
  '/obchodni-podminky',
  '/platebni-podminky',
  '/reklamace',
  '/faq',
]);

const isPublicHeaderPath = (pathname) => {
  if (publicPages.has(pathname)) return true;
  return pathname.startsWith('/programy') || pathname.startsWith('/catalog');
};

const handleAnchorClick = (event, href) => {
  if (!href.startsWith('/#') || window.location.pathname !== '/') return;
  const target = document.getElementById(href.slice(2));
  if (!target) return;
  event.preventDefault();
  window.history.replaceState(null, '', href);
  target.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

const navLinkClass =
  'text-[15px] font-semibold text-[#192938] transition-colors hover:text-[#B18152]';

const ctaClass =
  'inline-flex h-[54px] items-center justify-center gap-3 rounded-[15px] bg-[#192938] px-[23px] text-[15px] font-bold text-white shadow-[0_14px_34px_rgba(25,41,56,0.16)] transition-all hover:-translate-y-0.5 hover:bg-[#B18152]';

const BudezivoLogo = ({ showText = true, className = '' }) => (
  <div className={`flex items-center ${className}`}>
    <img
      src="/logo-budezivo.svg"
      alt="Budeživo.cz"
      className={showText ? 'block h-auto w-[161px]' : 'block h-auto w-[44px] object-left'}
    />
  </div>
);

export const Header = ({ minimal = false }) => {
  const { user, logout } = useContext(AuthContext);
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isPublicPage = isPublicHeaderPath(location.pathname);
  const showMarketingNav = isPublicPage && !user && !minimal;

  const renderNavLink = ({ label, href }) => (
    <a
      key={label}
      href={href}
      className={navLinkClass}
      onClick={(event) => {
        handleAnchorClick(event, href);
        setMobileOpen(false);
      }}
    >
      {label}
    </a>
  );

  return (
    <header className="sticky top-0 z-50 border-b border-[#e8e1d9] bg-[#f7f4f0]/96 backdrop-blur">
      <div className="mx-auto grid h-[86px] max-w-[1235px] grid-cols-[minmax(170px,1fr)_auto_minmax(270px,1fr)] items-center gap-8 px-6 max-[1080px]:flex max-[1080px]:h-[72px] max-[1080px]:justify-between">
        <Link to="/" className="flex items-center justify-self-start" data-testid="logo-link">
          <BudezivoLogo showText />
        </Link>

        {showMarketingNav && (
          <nav className="flex items-center gap-12 justify-self-center max-[1080px]:hidden">
            {mainNav.map(renderNavLink)}
          </nav>
        )}

        <div className="flex items-center justify-end gap-8 justify-self-end max-[1080px]:hidden">
          {user ? (
            <>
              <Link to="/admin" className={navLinkClass} data-testid="admin-dashboard-link">
                Přehled
              </Link>
              <button type="button" onClick={logout} className={`${navLinkClass} inline-flex items-center gap-2`} data-testid="logout-button">
                <LogOut className="h-4 w-4" />
                Odhlásit
              </button>
            </>
          ) : (
            showMarketingNav && (
              <>
                <Link to="/login" className={navLinkClass} data-testid="login-link">
                  Přihlásit se
                </Link>
                <Link to="/kontakt" className={ctaClass} data-testid="register-link">
                  Domluvit ukázku
                  <ArrowRight className="h-5 w-5" />
                </Link>
              </>
            )
          )}
        </div>

        {showMarketingNav && (
          <button
            type="button"
            className="hidden rounded-lg p-2 text-[#192938] max-[1080px]:inline-flex"
            onClick={() => setMobileOpen((open) => !open)}
            aria-label={mobileOpen ? 'Zavřít menu' : 'Otevřít menu'}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X className="h-7 w-7" /> : <Menu className="h-7 w-7" />}
          </button>
        )}
      </div>

      {showMarketingNav && mobileOpen && (
        <div className="fixed left-3 right-3 top-[78px] z-50 grid gap-5 rounded-[14px] border border-[#e8e1d9] bg-white p-6 shadow-[0_20px_50px_rgba(25,41,56,0.15)] md:hidden">
          {mainNav.map(renderNavLink)}
          <Link to="/login" className={navLinkClass} onClick={() => setMobileOpen(false)}>
            Přihlásit se
          </Link>
          <Link to="/kontakt" className={ctaClass} onClick={() => setMobileOpen(false)}>
            Domluvit ukázku
            <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
      )}
    </header>
  );
};

export { BudezivoLogo };
