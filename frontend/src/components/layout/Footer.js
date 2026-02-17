import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from '../../i18n/useTranslation';

export const Footer = () => {
  const { t } = useTranslation();

  return (
    <footer className="bg-slate-800 text-white py-12 mt-24">
      <div className="max-w-7xl mx-auto px-4 md:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-xl font-bold mb-4">KulturaBooking</h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              {t('hero.subtitle')}
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-4">{t('nav.home')}</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/" className="text-slate-300 hover:text-white transition-colors">
                  {t('footer.about')}
                </Link>
              </li>
              <li>
                <Link to="/#pricing" className="text-slate-300 hover:text-white transition-colors">
                  {t('footer.pricing')}
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-4">{t('nav.login')}</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/login" className="text-slate-300 hover:text-white transition-colors">
                  {t('footer.login')}
                </Link>
              </li>
              <li>
                <Link to="/register" className="text-slate-300 hover:text-white transition-colors">
                  {t('nav.register')}
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-4">{t('footer.contact')}</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="#" className="text-slate-300 hover:text-white transition-colors">
                  {t('footer.gdpr')}
                </a>
              </li>
              <li>
                <a href="#" className="text-slate-300 hover:text-white transition-colors">
                  {t('footer.contact')}
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-slate-700 text-center text-sm text-slate-400">
          <p>{t('footer.copyright')}</p>
        </div>
      </div>
    </footer>
  );
};
