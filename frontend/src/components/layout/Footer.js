import React from 'react';
import { Link } from 'react-router-dom';

// Minimalistické logo pro footer
const BudezivoLogoFooter = () => (
  <div className="flex items-center gap-2">
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
    <span className="font-bold text-white text-xl tracking-tight">
      Budeživo<span className="text-[#C4AB86]">.cz</span>
    </span>
  </div>
);

export const Footer = () => {
  return (
    <footer className="bg-[#2B3E50] text-white py-12 mt-24">
      <div className="max-w-7xl mx-auto px-4 md:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <BudezivoLogoFooter />
            <p className="text-slate-300 text-sm leading-relaxed mt-4">
              Rezervační systém pro muzea, galerie a knihovny, který zjednodušuje správu školních a skupinových programů.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Produkt</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="#funkce" className="text-slate-300 hover:text-white transition-colors">
                  Funkce
                </a>
              </li>
              <li>
                <a href="#pricing" className="text-slate-300 hover:text-white transition-colors">
                  Tarify
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Účet</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/login" className="text-slate-300 hover:text-white transition-colors">
                  Přihlášení
                </Link>
              </li>
              <li>
                <Link to="/register" className="text-slate-300 hover:text-white transition-colors">
                  Registrace
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Právní</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/gdpr" className="text-slate-300 hover:text-white transition-colors">
                  Ochrana osobních údajů
                </Link>
              </li>
              <li>
                <a href="mailto:info@bubezivo.cz" className="text-slate-300 hover:text-white transition-colors">
                  Kontakt
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-slate-600 text-center text-sm text-slate-400">
          <p>&copy; 2026 Bubeživo.cz. Všechna práva vyhrazena.</p>
        </div>
      </div>
    </footer>
  );
};
